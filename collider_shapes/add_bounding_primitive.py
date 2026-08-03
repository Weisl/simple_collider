import queue
import subprocess
import threading

import blf
import bmesh
import bpy
import gpu
import mathutils
import numpy
import time
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix, Quaternion

from .. import __package__ as base_package
from ..bmesh_operations.mesh_edit import delete_non_selected_verts
from ..bmesh_operations.mesh_split_by_island import create_objs_from_island
from ..groups.user_groups import set_object_color, set_default_group_values
from ..properties.constants import DECIMATE_NAME, VALID_OBJECT_TYPES
from ..pyshics_materials.material_functions import assign_physics_material, create_default_material, \
    set_active_physics_material, set_material

# How long the viewport-navigation HUD dimming stays on after the view was
# last seen changing (see draw_viewport_overlay). Short enough to feel
# responsive once navigation actually stops, long enough to bridge the gap
# between individual redraw callbacks.
NAVIGATION_HOLD_SECONDS = 0.2

# How long a heavy modifier re-evaluation (decimate ratio / remesh voxel
# size) waits for the dragged value to stop changing before it actually
# runs. Without this, every MOUSEMOVE delta while dragging kicks off a new
# evaluation; for slow operations (e.g. voxel remesh on a dense mesh) each
# evaluation starts before the previous one finishes and the viewport falls
# behind the input, stuttering/freezing (#641).
MODIFIER_DEBOUNCE_SECONDS = 0.15


def alignObjects(new, old):
    """Align two objects"""
    new.matrix_world = old.matrix_world


def create_name_number(name, nr, digits=3):
    return f"{name}_{nr:0{digits}}"


def matches_local_collider_collection(collection, base_name):
    """True if `collection` is a local collection matching `base_name`,
    either exactly or via this addon's own "_NN" disambiguation suffix
    (e.g. "Colliders_01").

    A local collection named `base_name` may already exist elsewhere in
    the file - e.g. another scene's own collider collection - since local
    collection names are unique file-wide, not per scene. A same-named new
    collection then gets our own "_NN" suffix on creation (see
    _next_available_local_name), so later lookups must recognize that
    suffixed form as ours too, or they'd fail to find it and create yet
    another new collection on every call.
    """
    if collection.library is not None:
        return False
    if collection.name == base_name:
        return True
    suffix_prefix = base_name + '_'
    return collection.name.startswith(suffix_prefix) and collection.name[len(suffix_prefix):].isdigit()


def _next_available_local_name(base_name):
    """Return `base_name`, or `base_name` with our own "_NN" suffix
    (01, 02, ...) if a local collection already owns `base_name`.

    Local collection names are unique file-wide, so a second scene's own
    collider collection needs a distinct name. Blender's own auto-rename
    would use ".001"; this addon uses "_NN" instead, matched by
    matches_local_collider_collection(). Only local names are checked -
    a same-named library-linked collection does not force a rename, since
    it is never treated as ours (see matches_local_collider_collection).
    """
    local_names = {c.name for c in bpy.data.collections if c.library is None}
    if base_name not in local_names:
        return base_name
    i = 1
    while create_name_number(base_name, i, digits=2) in local_names:
        i += 1
    return create_name_number(base_name, i, digits=2)


def _local_child_collection(parent_collection, name):
    """Return the local (non-library-linked) direct child of
    `parent_collection` matching `name` (exactly or via our "_NN"
    suffix), or None.

    Matching only among direct children - rather than a global
    `bpy.data.collections` lookup - keeps collider collections scoped to
    the scene they belong to: each scene gets its own collection, so
    colliders from one scene are never bled into another via a shared
    collection.
    """
    for child in parent_collection.children:
        if matches_local_collider_collection(child, name):
            return child
    return None


def set_origin_to_center_of_mass(obj, depsgraph=None):
    """
    Sets the origin of the given object to its center of mass.

    Parameters:
    obj (bpy.types.Object): The object whose origin will be set to the center of mass.
    depsgraph: Optional pre-evaluated depsgraph.  When processing many objects in a
        loop, pass a single depsgraph obtained before the loop to avoid O(N²)
        re-evaluations: each obj.location assignment dirties the depsgraph, and
        evaluated_depsgraph_get() forces a full re-evaluation on every call.
    """
    if obj.type != 'MESH':
        print(f"Object '{obj.name}' is not a mesh. Cannot calculate center of mass.")
        return

    # Ensure the object has up-to-date evaluated data
    if depsgraph is None:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.data

    # Calculate center of mass using numpy for better performance
    if len(mesh.vertices) == 0:
        print(f"Object '{obj.name}' has no vertices. Cannot calculate center of mass.")
        return
    
    # Use numpy for faster vertex operations. obj.matrix_world is a 4x4
    # mathutils.Matrix; numpy's `@` can't multiply it directly against an
    # (N, 3) array (shape mismatch), so the rotation/scale submatrix and
    # translation are applied explicitly instead.
    verts_local = numpy.array([v.co for v in mesh.vertices])
    mat_world = numpy.array(obj.matrix_world)
    verts_world = verts_local @ mat_world[:3, :3].T + mat_world[:3, 3]
    com = numpy.mean(verts_world, axis=0)

    # Calculate the offset
    offset = obj.matrix_world.inverted() @ mathutils.Vector(com)

    # Apply the offset to the object's own (base) mesh vertices. Note:
    # `verts_local`/`mesh` above are the evaluated (post-modifier) mesh, used
    # only to compute the center of mass - modifiers such as the convex hull
    # / decimate modifiers used by Auto Convex can change the vertex count,
    # so its vertices no longer line up 1:1 with obj.data.vertices here.
    for vertex in obj.data.vertices:
        vertex.co = vertex.co - offset

    # Move the object's origin to the center of mass
    obj.location = mathutils.Vector(com)

def geometry_node_group_empty_new():
    group = bpy.data.node_groups.new("Convex_Hull", 'GeometryNodeTree')
    if bpy.app.version < (4, 00):
        # legacy support
        group.inputs.new('NodeSocketGeometry', "Geometry")
        group.outputs.new('NodeSocketGeometry', "Geometry")

    else:
        group.interface.new_socket('Geometry', description="", in_out='INPUT', socket_type='NodeSocketGeometry',
                                   parent=None)
        group.interface.new_socket('Geometry', description="", in_out='OUTPUT', socket_type='NodeSocketGeometry',
                                   parent=None)

    input_node = group.nodes.new('NodeGroupInput')
    output_node = group.nodes.new('NodeGroupOutput')
    output_node.is_active_output = True

    input_node.select = output_node.select = False

    input_node.location.x = -200 - input_node.width
    output_node.location.x = 200

    group.links.new(output_node.inputs[0], input_node.outputs[0])

    return group


def draw_modal_item(self, context, font_id, i, vertical_px_offset, left_margin, label, value=None, type='default',
                    key='',
                    highlight=False, padding_bottom=0):
    """Draw label in the 3D Viewport"""

    # get colors from preferences
    col_default = self.prefs.modal_color_default
    color_title = self.prefs.modal_color_title
    color_ignore_input = [0.604, 0.616, 0.651, 0.7]  # brand "text_muted" token

    # operator colors
    color_enum = self.prefs.modal_color_enum
    color_modal = self.prefs.modal_color_modal
    color_bool = self.prefs.modal_color_bool
    color_highlight = self.prefs.modal_color_highlight
    color_error = self.prefs.modal_color_error
    color_navigation = self.prefs.modal_color_navigation

    # system.ui_scale reflects the OS/monitor-driven DPI scale (e.g. ~2.5 on a
    # 4K/5K display); view.ui_scale is the user's manual "Resolution Scale"
    # preference on top of that. Blender's native UI is scaled by both, so
    # the overlay needs both too or it stays a fixed pixel size on HiDPI
    # screens while the rest of the UI scales up (issue #623).
    font_size = int(self.prefs.modal_font_size * context.preferences.system.ui_scale
                    * context.preferences.view.ui_scale / 3.6)

    if bpy.app.version < (4, 00):
        # legacy support
        blf.size(font_id, 72, font_size)
    else:
        blf.size(font_id, font_size)

    color_map = {
        'error': color_error,
        'key_title': color_title,
        'disabled': color_ignore_input,
        'title': color_title,
        'default': col_default,
        'bool': color_bool,
        'enum': color_enum,
        'modal': color_modal
    }

    # navigating the viewport or holding ALT to ignore input takes over every row
    # (except the title, which stays the constant branded header) in its own
    # color, distinct from both the normal per-row colors and the drag highlight.
    # A setting currently being dragged takes over its own line in the highlight
    # color, not just its value, so it's obvious at a glance which one is live.
    ignoring_input = self.ignore_input or self.navigation
    if ignoring_input and type != 'title':
        label_color = color_navigation
    elif highlight:
        label_color = color_highlight
    else:
        label_color = color_map.get(type, col_default)

    blf.color(font_id, *label_color)
    blf.position(font_id, left_margin, padding_bottom + (i * vertical_px_offset), 0)
    blf.draw(font_id, label)

    if key:
        # key hints are a secondary cue, not a second label - dim them so the
        # label color still reads as the primary signal
        key_color = list(label_color)
        key_color[3] *= 0.5
        blf.color(font_id, *key_color)
        blf.position(font_id, left_margin + 220 / 20 * font_size, padding_bottom + (i * vertical_px_offset), 0)
        blf.draw(font_id, key)

    if value:
        if ignoring_input:
            color = color_navigation
        elif highlight:
            color = color_highlight
        elif type == 'bool':
            # let True/False read as on/off at a glance, not just as text
            color = col_default if value == 'True' else color_ignore_input
        elif type == 'disabled':
            color = color_ignore_input
        else:  # type == 'default':
            color = col_default

        blf.color(font_id, color[0], color[1], color[2], color[3])
        blf.position(font_id, left_margin + 290 / 20 * font_size, padding_bottom + (i * vertical_px_offset), 0)
        blf.draw(font_id, value)

    return i + 1


def draw_viewport_overlay(self, context):
    """Draw 3D viewport overlay for the modal operator"""
    items = []

    # Detecting "is the user currently navigating" from event types seen in
    # modal() doesn't work reliably: an MMB orbit drag hands its MOUSEMOVE
    # events - and usually even the terminating release - to Blender's own
    # view3d.rotate modal operator before they ever reach this operator's
    # modal(), so nothing observed there can tell whether a drag is still
    # in progress. This draw callback runs on every actual repaint though,
    # and Blender keeps repainting continuously for as long as the view is
    # visibly changing - so comparing the region's view matrix frame to
    # frame is a direct, reliable "is navigation actually happening" signal
    # instead of an event-based guess.
    region_3d = getattr(context.space_data, 'region_3d', None)
    if region_3d is not None:
        view_snapshot = (region_3d.view_matrix.copy(), region_3d.view_distance)
        if self.navigation_view_snapshot is not None and view_snapshot != self.navigation_view_snapshot:
            self.navigation_hold_until = time.time() + NAVIGATION_HOLD_SECONDS
            self.arm_navigation_timer()
        self.navigation_view_snapshot = view_snapshot
    self.navigation = time.time() < self.navigation_hold_until

    # An external subprocess job (CoACD/V-HACD, see _launch_async_process()
    # below) is running asynchronously. None of the per-row settings below
    # (D/S/A/etc.) apply to anything yet - there are no colliders to adjust
    # until the job finishes - so showing them as if they were live would be
    # misleading. Replace the whole settings HUD with a dedicated status
    # overlay instead, and skip building it at all.
    if getattr(self, '_async_process', None) is not None:
        draw_async_job_overlay(self, context)
        return

    self.valid_input_selection = True if len(self.new_colliders_list) > 0 else False
    if self.use_space:
        label = "Global/Local"
        type = 'enum'
        value = str(self.my_space)
        item = {'label': label, 'value': value, 'key': '(G/L)', 'type': type, 'highlight': False}
        items.append(item)

    if self.use_creation_mode:
        label = "Creation Mode "
        value = self.creation_mode[self.creation_mode_idx]
        item = {'label': label, 'value': value, 'key': '(M)', 'type': 'enum', 'highlight': False}
        items.append(item)

    if self.collider_groups_enabled:
        label = "Collider Group"
        value = self.collision_groups[self.collision_group_idx].name

        item = {'label': label, 'value': value, 'key': '(T)', 'type': 'enum', 'highlight': False}
        items.append(item)

    if context.space_data.shading.type == 'SOLID':
        label = "Preview Mode"
        value = self.shading_modes[self.shading_idx]
        type = 'enum'
    else:
        label = "Solid View"
        value = str(self.is_solidmode)
        type = 'bool'
    item = {'label': label, 'value': value, 'key': '(V)', 'type': type, 'highlight': False}
    items.append(item)

    if self.use_shape_change:
        label = "Shape Overwrite"
        value = self.get_shape_name()
        item = {'label': label, 'value': value, 'key': '(Q)', 'type': 'enum', 'highlight': False}
        items.append(item)

    if self.use_cylinder_axis:
        label = "Cylinder Axis"
        value = str(self.cylinder_axis)
        item = {'label': label, 'value': value, 'key': '(X/Y/Z)', 'type': 'enum', 'highlight': False}
        items.append(item)

    if self.use_capsule_axis:
        label = "Capsule Axis"
        value = str(self.cylinder_axis)
        creation_mode = self.creation_mode[
            self.creation_mode_idx] if self.obj_mode == 'OBJECT' else self.creation_mode_edit[self.creation_mode_idx]

        if self.use_loose_mesh:
            type = 'disabled'
        else:
            type = 'enum'
        item = {'label': label, 'value': value, 'key': '(X/Y/Z)', 'type': type, 'highlight': False}
        items.append(item)

    # settings above persist between operator calls; settings below reset every run -
    # this row count marks where the HUD divider between the two groups goes
    persistent_row_count = len(items)

    if self.use_modifier_stack:
        label = "Use Modifiers "
        value = str(self.my_use_modifier_stack)
        item = {'label': label, 'value': value, 'key': '(P)', 'type': 'bool', 'highlight': False}
        items.append(item)

    # mode check is here because keep original mesh doesn't work for EDIT mode atm.
    if self.use_keep_original_materials:
        label = "Keep Original Materials"

        value = str(self.keep_original_material)
        # Currently only supported in OBJECT mode
        type = 'bool'
        item = {'label': label, 'value': value, 'key': '(O)', 'type': type, 'highlight': False}
        items.append(item)

    if self.use_keep_original_name:
        label = "Keep Original Name"

        value = str(self.keep_original_name)
        # Currently only supported in OBJECT mode
        if self.obj_mode == 'OBJECT':
            type = 'bool'
        else:
            type = 'disabled'
        item = {'label': label, 'value': value, 'key': '(N)', 'type': type, 'highlight': False}
        items.append(item)

    if self.use_diagonal_fill:
        label = "Diagonal Fill"
        value = str(self.diagonal_fill)
        item = {'label': label, 'value': value, 'key': '(F)', 'type': 'bool', 'highlight': False}
        items.append(item)

    items.append({'label': "Toggle X Ray", 'value': str(self.x_ray), 'key': '(C)', 'type': 'bool', 'highlight': False})
    items.append({'label': "Use Loose Islands", 'value': str(self.use_loose_mesh), 'key': '(I)', 'type': 'bool',
                  'highlight': False})
    items.append({'label': "Join Primitives", 'value': str(self.join_primitives), 'key': '(J)', 'type': 'bool',
                  'highlight': False})

    if self.shading_modes[self.shading_idx] == 'OBJECT':
        label = "Opacity"
        value = self.format_modal_value(self.opacity_active, self.current_settings_dic['alpha'])
        item = {'label': label, 'value': value, 'key': '(A)', 'type': 'modal', 'highlight': self.opacity_active}
        items.append(item)

    label = "Shrink/Inflate"
    value = self.format_modal_value(self.displace_active, self.current_settings_dic['displace_offset'])
    item = {'label': label, 'value': value, 'key': '(S)', 'type': 'modal', 'highlight': self.displace_active}
    items.append(item)

    if self.use_sphere_segments:
        label = "Sphere Segments "
        value = self.format_modal_value(self.sphere_segments_active, self.current_settings_dic['sphere_segments'],
                                        is_int=True)
        item = {'label': label, 'value': value, 'key': '(R)', 'type': 'modal', 'highlight': self.sphere_segments_active}
        items.append(item)

    if self.use_capsule_segments:
        label = "Capsule Segments "
        value = self.format_modal_value(self.capsule_segments_active, self.current_settings_dic['capsule_segments'],
                                        is_int=True)
        item = {'label': label, 'value': value, 'key': '(R)', 'type': 'modal',
                'highlight': self.capsule_segments_active}
        items.append(item)

    if self.use_decimation:
        label = "Decimate Ratio"
        value = self.format_modal_value(self.decimate_active, self.current_settings_dic['decimate'])
        item = {'label': label, 'value': value, 'key': '(D)', 'type': 'modal', 'highlight': self.decimate_active}
        items.append(item)

    if self.use_height_multiplier:
        label = "Height Multiplier"
        value = self.format_modal_value(self.height_active, self.current_settings_dic['height_mult'])
        item = {'label': label, 'value': value, 'key': '(H)', 'type': 'modal', 'highlight': self.height_active}
        items.append(item)

    if self.use_width_multiplier:
        label = "Width Multiplier"
        value = self.format_modal_value(self.width_active, self.current_settings_dic['width_mult'])
        item = {'label': label, 'value': value, 'key': '(W)', 'type': 'modal', 'highlight': self.width_active}
        items.append(item)

    if self.use_cylinder_segments:
        label = "Segments"
        value = self.format_modal_value(self.cylinder_segments_active, self.current_settings_dic['cylinder_segments'],
                                        is_int=True)
        key = '(E)'
        type = 'modal'
        highlight = self.cylinder_segments_active

        item = {'label': label, 'value': value, 'key': key, 'type': type, 'highlight': highlight}
        items.append(item)

    if self.use_remesh:
        label = "Voxel Size"
        value = self.format_modal_value(self.remesh_active, self.current_settings_dic['voxel_size_multiplier'])
        key = '(R)'
        type = 'modal'
        highlight = self.remesh_active

        item = {'label': label, 'value': value, 'key': key, 'type': type, 'highlight': highlight}
        items.append(item)

    label = 'Operator Settings'
    type = 'title'
    item = {'label': label, 'value': None, 'key': '', 'type': type, 'highlight': False}
    items.append(item)
    title_row = len(items)

    if self.valid_input_selection:
        if self.navigation:
            label = 'VIEWPORT NAVIGATION'
            type = 'key_title'
            highlight = True
            item = {'label': label, 'value': None, 'key': '', 'type': type, 'highlight': highlight}
            items.append(item)

        elif self.ignore_input:
            label = 'IGNORE INPUT (ALT)'
            type = 'key_title'
            highlight = True
            item = {'label': label, 'value': None, 'key': '', 'type': type, 'highlight': highlight}
            items.append(item)

        elif self.numeric_input_active:
            label = 'TYPE VALUE - ENTER TO CONFIRM, ESC TO CANCEL'
            type = 'key_title'
            highlight = True
            item = {'label': label, 'value': None, 'key': '', 'type': type, 'highlight': highlight}
            items.append(item)

    else:  # Invalid selection (No colliders to be generated)
        label = 'Selection Invalid'
        type = 'error'
        item = {'label': label, 'value': None, 'key': '', 'type': type, 'highlight': False}
        items.append(item)

    # text properties
    font_id = 0  # XXX, need to find out how best to get this.
    font_size = int(self.prefs.modal_font_size * context.preferences.system.ui_scale
                    * context.preferences.view.ui_scale / 3.6)
    vertical_px_offset = font_size * 1.5
    left_text_margin = bpy.context.area.width / 2 - 190 / 20 * font_size

    # breathing room above the title and below the bottom-most row, instead of
    # the text sitting flush against the backdrop edges
    row_padding = font_size * 0.5

    # backdrop box
    box_left = bpy.context.area.width / 2 - 240 / 20 * font_size
    box_right = bpy.context.area.width / 2 + 260 / 20 * font_size
    box_top = font_size * len(items) * 1.75 + row_padding * 2
    box_bottom = 10

    prefs = self.prefs
    color = prefs.modal_box_color

    if prefs.use_modal_box:
        draw_2d_backdrop(self, context, box_left, box_right, box_top, box_bottom, color)

        # brand card treatment: a neutral hairline frame with a colored top edge,
        # matching the store page's .grid-card--top / .section--hairline convention.
        # Opaque colors (no alpha blending) so the lines read the same regardless
        # of what's behind them in the viewport, instead of the previous low-alpha
        # overlay looking faint or uneven over a busy scene.
        frame_color = (0.204, 0.212, 0.243, 1.0)  # brand "border" token
        accent_color = (0.133, 0.773, 0.369, 1.0)  # brand accent
        frame_px = 1
        accent_px = 3
        draw_2d_backdrop(self, context, box_left, box_right, box_top, box_top - accent_px, accent_color)
        draw_2d_backdrop(self, context, box_left, box_right, box_bottom + frame_px, box_bottom, frame_color)
        draw_2d_backdrop(self, context, box_left, box_left + frame_px, box_top - accent_px, box_bottom, frame_color)
        draw_2d_backdrop(self, context, box_right - frame_px, box_right, box_top - accent_px, box_bottom, frame_color)

        # divider rules, full width like the brand's section hairlines: split the
        # header from the settings, and the settings that persist between operator
        # calls from the ones that reset every run.
        def draw_rule(row):
            y = row_padding + (row + 0.5) * vertical_px_offset
            draw_2d_backdrop(self, context, box_left, box_right, y + frame_px / 2, y - frame_px / 2, frame_color)

        if title_row > 1:
            draw_rule(title_row - 1)
        if 0 < persistent_row_count < title_row - 1:
            draw_rule(persistent_row_count)

    for i, item in enumerate(items):
        draw_modal_item(self, context, font_id, i + 1, vertical_px_offset, left_text_margin, item['label'],
                        value=item['value'],
                        key=item['key'], type=item['type'], highlight=item['highlight'],
                        padding_bottom=row_padding)


def draw_async_job_overlay(self, context):
    """Centered status overlay shown in place of the normal settings HUD
    while an external subprocess job (CoACD/V-HACD, launched via
    _launch_async_process()) is running. Deliberately not just another row
    in the regular HUD: that list reads as "these are live, interactive
    settings", which isn't true while a job is running - there's nothing to
    adjust until it produces colliders. A distinct, centered, warning-styled
    block makes that state unambiguous instead."""
    region = context.region
    if region is None:
        return

    prefs = self.prefs
    font_id = 0
    font_size = int(prefs.modal_font_size * context.preferences.system.ui_scale
                    * context.preferences.view.ui_scale / 3.6)
    title_font_size = int(font_size * 1.5)

    elapsed = time.time() - getattr(self, '_async_start_time', time.time())
    job_label = getattr(self, '_async_job_label', 'PROCESSING')
    status = getattr(self, '_async_status_text', '')

    lines = [(f'RUNNING {job_label.upper()}', title_font_size, prefs.modal_color_error)]
    if status:
        lines.append((status.upper(), font_size, prefs.modal_color_default))
    lines.append((f'{elapsed:0.0f}S ELAPSED', font_size, prefs.modal_color_default))
    lines.append(('ESC TO CANCEL', font_size, prefs.modal_color_navigation))

    line_height = int(font_size * 1.6)
    row_padding = font_size * 0.7
    box_height = line_height * len(lines) + row_padding * 2
    box_width = 420 / 20 * font_size

    center_x = region.width / 2
    center_y = region.height / 2

    box_left = center_x - box_width / 2
    box_right = center_x + box_width / 2
    box_top = center_y + box_height / 2
    box_bottom = center_y - box_height / 2

    if prefs.use_modal_box:
        draw_2d_backdrop(self, context, box_left, box_right, box_top, box_bottom, prefs.modal_box_color)

        # warning-red accent (vs. the brand-green accent on the normal settings
        # HUD) so this reads as a distinct, attention-worthy state at a glance.
        frame_color = (0.204, 0.212, 0.243, 1.0)
        accent_color = (0.902, 0.302, 0.302, 1.0)
        frame_px = 1
        accent_px = 3
        draw_2d_backdrop(self, context, box_left, box_right, box_top, box_top - accent_px, accent_color)
        draw_2d_backdrop(self, context, box_left, box_right, box_bottom + frame_px, box_bottom, frame_color)
        draw_2d_backdrop(self, context, box_left, box_left + frame_px, box_top - accent_px, box_bottom, frame_color)
        draw_2d_backdrop(self, context, box_right - frame_px, box_right, box_top - accent_px, box_bottom, frame_color)

    y = box_top - row_padding - line_height * 0.75
    for text, size, color in lines:
        if bpy.app.version < (4, 00):
            blf.size(font_id, 72, size)
        else:
            blf.size(font_id, size)
        blf.color(font_id, *color)
        text_width = blf.dimensions(font_id, text)[0]
        blf.position(font_id, center_x - text_width / 2, y, 0)
        blf.draw(font_id, text)
        y -= line_height


def draw_2d_backdrop(self, context, left, right, top, bottom, color):
    midWidth = bpy.context.area.width / 2

    vertices = (
        (left, bottom), (right, bottom),
        (left, top), (right, top))

    indices = (
        (0, 1, 2), (2, 1, 3))

    if bpy.app.version < (4, 00):
        # legacy support
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    else:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def get_loc_matrix(location):
    """get location matrix"""
    return Matrix.Translation(location)


def get_rot_matrix(rotation):
    """get rotation matrix"""
    return rotation.to_matrix().to_4x4()


def get_sca_matrix(scale):
    """get scale matrix"""
    scale_mx = Matrix()
    for i in range(3):
        scale_mx[i][i] = scale[i]
    return scale_mx


def collision_dictionary(alpha, offset, decimate, sphere_segments, cylinder_segments, capsule_segments,
                         voxel_size, height_mult, width_mult):
    dict = {}
    dict['alpha'] = alpha
    dict['displace_offset'] = offset
    dict['decimate'] = decimate
    dict['sphere_segments'] = sphere_segments
    dict['cylinder_segments'] = cylinder_segments
    dict['capsule_segments'] = capsule_segments
    dict['voxel_size_multiplier'] = voxel_size
    dict['height_mult'] = height_mult
    dict['width_mult'] = width_mult

    return dict


def add_weld_modifier(context, bounding_object):
    # add displacement modifier and safe it to manipulate the strength in the modal operator
    modifier = bounding_object.modifiers.new(name="Collider_weld", type='WELD')


class OBJECT_OT_add_bounding_object():
    """Abstract parent class for modal collider_shapes contain common methods and properties for all add bounding
    object collider_shapes"""
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}
    # GRAB_CURSOR + BLOCKING enables wrap-around mouse feature.
    bm = []

    # Shared external-subprocess-job plumbing, used by both
    # COACD_OT_convex_decomposition and VHACD_OT_convex_decomposition to run
    # their CLI backends asynchronously via bpy.app.timers instead of
    # blocking Blender's main thread with Popen.wait() (#660). Both
    # operators drive their own poll/finish/cancel state machines - the
    # per-tool flow genuinely differs (CoACD has an extra per-hull decimate
    # pass, V-HACD doesn't) - but share these three generic pieces: how a
    # subprocess is launched and its stdout captured, how that stdout is
    # drained into a live status string, and how that status is drawn (see
    # draw_async_job_overlay() above). Subclasses set self._async_process /
    # self._async_start_time / self._async_job_label and override
    # _parse_progress_line() for their own CLI's output format.
    def _launch_async_process(self, cmd, cwd):
        """Launch cmd with its stdout/stderr piped through a daemon reader
        thread into a queue, instead of letting it inherit the console.
        _drain_async_progress() then pulls from that queue on Blender's main
        thread (never blocking it) to keep the status overlay live.

        The reader splits on '\\r' as well as '\\n': some CLIs (V-HACD) print
        progress updates separated only by carriage returns, the same way a
        terminal progress bar would - readline() alone would silently buffer
        all of those into one giant line until a real newline eventually
        showed up, making progress updates arrive in chunky, stale bursts
        instead of smoothly.
        """
        process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        q = queue.Queue()

        def _reader():
            try:
                buf = ''
                while True:
                    ch = process.stdout.read(1)
                    if not ch:
                        break
                    if ch in ('\n', '\r'):
                        if buf:
                            q.put(buf)
                            buf = ''
                    else:
                        buf += ch
                if buf:
                    q.put(buf)
            except Exception:
                pass

        threading.Thread(target=_reader, daemon=True).start()

        self._async_stdout_queue = q
        self._async_status_text = ''
        return process

    def _parse_progress_line(self, line):
        """Override per-operator: return an updated status string for this
        line, or None if the line doesn't change the current status. Default
        implementation never updates - the overlay just shows elapsed time."""
        return None

    def _drain_async_progress(self):
        """Pull whatever lines the reader thread has queued since the last
        poll and refresh self._async_status_text via _parse_progress_line().
        queue.Queue.get_nowait() never blocks - it either returns
        immediately or raises Empty."""
        q = getattr(self, '_async_stdout_queue', None)
        if q is None:
            return
        while True:
            try:
                line = q.get_nowait()
            except queue.Empty:
                break
            status = self._parse_progress_line(line)
            if status is not None:
                self._async_status_text = status

    @staticmethod
    def calculate_center_of_mass(obj):
        """calculate center of mass. """
        x, y, z = [sum([(obj.matrix_world.inverted() @ v.co)[i] for v in obj.data.vertices]) for i
                   in range(3)]
        count = float(len(obj.data.vertices))
        center = obj.matrix_world @ (Vector((x, y, z)) / count)

        return center

    @staticmethod
    def set_custom_origin_location(obj, center_point):
        """Set the origin of an object to the custom origin location. Only works if the object is not rotated or
        scaled at the moment"""
        # https://blender.stackexchange.com/questions/35825/changing-object-origin-to-arbitrary-point-without-origin-set
        obj.data.transform(mathutils.Matrix.Translation(-center_point))
        obj.location += center_point

    @staticmethod
    def apply_transform(obj, rotation=False, scale=True):
        """Apply transformations to object"""
        mx = obj.matrix_world
        loc, rot, sca = mx.decompose()

        # apply the current transformations on the mesh level
        if scale and rotation:
            mesh_matrix = get_rot_matrix(rot) @ get_sca_matrix(sca)
            apply_matrix = get_loc_matrix(loc) @ get_rot_matrix(Quaternion()) @ get_sca_matrix(Vector.Fill(3, 1))
        elif rotation:
            mesh_matrix = get_rot_matrix(rot)
            apply_matrix = get_loc_matrix(loc) @ get_rot_matrix(Quaternion()) @ get_sca_matrix(sca)
        elif scale:
            mesh_matrix = get_sca_matrix(sca)
            apply_matrix = get_loc_matrix(loc) @ get_rot_matrix(rot) @ get_sca_matrix(Vector.Fill(3, 1))

        obj.data.transform(mesh_matrix)
        obj.matrix_world = apply_matrix

    @staticmethod
    def set_custom_rotation(obj, rotation_matrix):
        """Rotate the origin based on a custom rotation matrix"""
        #
        ob_loc = obj.location.copy()

        # decompose the object matrix into it's location, rotation, scale components
        mx = obj.matrix_world
        loc, rot, sca = mx.decompose()

        # apply the current transformations on the mesh level
        mesh_matrix = rotation_matrix.inverted()
        apply_matrix = get_loc_matrix(loc) @ rotation_matrix @ get_sca_matrix(sca)

        # Apply matrices to mesh and object
        obj.data.transform(mesh_matrix)
        obj.matrix_world = apply_matrix

        # set the location back to the old location
        obj.location = ob_loc

    @classmethod
    def split_coordinates_xyz(cls, v_co_list):
        """Split a list of vertex locations into lists for the X Y Z component """
        positionsX = []
        positionsY = []
        positionsZ = []

        # generate a lists of all x, y and z coordinates to find the min and max
        for co in v_co_list:
            positionsX.append(co[0])
            positionsY.append(co[1])
            positionsZ.append(co[2])

        return positionsX, positionsY, positionsZ

    @classmethod
    def generate_bounding_box(cls, v_co):
        """get the min and max coordinates for the bounding box"""

        positionsX, positionsY, positionsZ = cls.split_coordinates_xyz(v_co)

        min_x = min(positionsX)
        min_y = min(positionsY)
        min_z = min(positionsZ)

        max_x = max(positionsX)
        max_y = max(positionsY)
        max_z = max(positionsZ)

        verts = [
            (max_x, max_y, min_z),
            (max_x, min_y, min_z),
            (min_x, min_y, min_z),
            (min_x, max_y, min_z),
            (max_x, max_y, max_z),
            (max_x, min_y, max_z),
            (min_x, min_y, max_z),
            (min_x, max_y, max_z),
        ]

        center_point = Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2))

        return verts, center_point

    @staticmethod
    def get_object_max_dimension(obj):
        """Get the maximum dimension of an object"""
        return max(obj.dimensions)

    @staticmethod
    def set_data_name(obj, new_name, data_suffix):
        """name object data based on object name"""
        data_name = new_name + data_suffix
        if data_name in bpy.data.meshes:
            bpy.data.meshes[data_name].name = 'deprecated_' + data_name

        obj.data.name = data_name
        return data_name

    @staticmethod
    def unique_name(name, digits=3, exclude=None, cache=None):
        """Function to find a unique name using a loop.

        cache, if provided, is a dict mapping base name → last used count.
        Callers that generate many names with the same base should pass a
        persistent dict so the search resumes from the last position rather
        than restarting at 1 every call (which would be O(N²) total lookups).
        """
        count = (cache.get(name, 0) if cache is not None else 0) + 1
        new_name = create_name_number(name, count, digits)

        while new_name in bpy.data.objects and new_name != exclude:
            count += 1
            new_name = create_name_number(name, count, digits)

        if cache is not None:
            cache[name] = count
        return new_name

    @staticmethod
    def custom_set_parent(context, parent, child):
        """Custom set parent"""
        # Direct Python assignment avoids bpy.ops.object.parent_set(), which
        # triggers a full depsgraph evaluation on every call.  With O(N)
        # islands that compounds to O(N) depsgraph rebuilds each growing more
        # expensive as more objects accumulate.  The confirmation loop manages
        # view_layer.update() calls explicitly; this function does not trigger one.
        #
        # Build the child's world matrix from loc/rot/sca rather than reading
        # matrix_world, which is only updated by the depsgraph.  When child.location
        # is set after the most recent depsgraph evaluation (as generate_cylinder_object
        # and create_sphere do), matrix_world is stale and would capture the old
        # cursor/origin position rather than the intended centre.  loc/rot/sca are
        # always current because they are stored directly on the object, not computed
        # by the depsgraph.
        mtx = Matrix.LocRotScale(child.location, child.rotation_euler, child.scale)
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()
        child.matrix_world = mtx

    @classmethod
    def bmesh(cls, bm):
        # append bmesh to class for it not to be deleted
        cls.bm.append(bm)

    @classmethod
    def class_collider_name(cls, shape_identifier, user_group, basename='Basename', exclude=None,
                            cache=None):
        prefs = bpy.context.preferences.addons[base_package].preferences
        new_name = cls.class_collider_name_base(shape_identifier, user_group, basename)
        return cls.unique_name(new_name, prefs.collision_digits, exclude=exclude, cache=cache)

    @classmethod
    def class_collider_name_base(cls, shape_identifier, user_group, basename='Basename'):
        """Build the collider name base (without the unique numeric suffix)."""
        prefs = bpy.context.preferences.addons[base_package].preferences
        separator = prefs.separator

        # Ignore rigid body extension/prefix in the base name when renaming
        if prefs.rigid_body_extension and basename:
            if prefs.rigid_body_naming_position == 'SUFFIX':
                end = prefs.rigid_body_separator + prefs.rigid_body_extension
                if basename.endswith(end):
                    basename = basename[:-(len(end))]
            else:
                start = prefs.rigid_body_extension + prefs.rigid_body_separator
                if basename.startswith(start):
                    basename = basename[len(start):]

        if prefs.replace_name:
            name = prefs.obj_basename
        else:
            name = basename

        if prefs.collider_groups_enabled:
            pre_suffix_components = [
                prefs.collision_string_prefix,
                cls.get_shape_pre_suffix(prefs, shape_identifier),
                user_group,
                prefs.collision_string_suffix
            ]
        else:  # prefs.collider_groups_enabled == False:
            pre_suffix_components = [
                prefs.collision_string_prefix,
                cls.get_shape_pre_suffix(prefs, shape_identifier),
                prefs.collision_string_suffix
            ]

        name_pre_suffix = ''
        if prefs.naming_position == 'SUFFIX':
            for comp in pre_suffix_components:
                if comp:
                    name_pre_suffix = name_pre_suffix + separator + comp
            return name + name_pre_suffix

        else:  # prefs.naming_position == 'PREFIX'
            for comp in pre_suffix_components:
                if comp:
                    name_pre_suffix = name_pre_suffix + comp + separator
            return name_pre_suffix + name

    def draw_callback_px(self, context):

        font_id = 0  # XXX, need to find out how best to get this.
        font_color = [0.5, 0.5, 0.5, 0.5]
        ui_scale = context.preferences.system.ui_scale * context.preferences.view.ui_scale
        font_size = int(20 * ui_scale)

        if bpy.app.version < (4, 00):
            # legacy support
            blf.size(font_id, 72, font_size)
        else:
            blf.size(font_id, font_size)

        blf.color(font_id, font_color[0], font_color[1], font_color[2], font_color[3])
        blf.position(font_id, 100 * ui_scale, 100 * ui_scale, 0)
        face_label = str(sum(self.face_counts))
        blf.draw(font_id, face_label)

    def collider_name(self, basename='Basename', exclude=None):
        self.basename = basename
        user_group = self.collision_groups[self.collision_group_idx].identifier
        return self.class_collider_name(shape_identifier=self.shape, user_group=user_group,
                                        basename=basename, exclude=exclude,
                                        cache=self._naming_cache)

    def get_shape_name(self):
        """ Return Shape String """
        if self.shape == 'box_shape':
            return 'BOX'
        elif self.shape == 'sphere_shape':
            return 'SPHERE'
        elif self.shape == 'capsule_shape':
            return 'CAPSULE'
        elif self.shape == 'convex_shape':
            return 'CONVEX'
        elif self.shape == 'voxel_shape':
            return 'VOXEL'
        else:  # identifier == 'mesh_shape':
            return 'MESH'

    @staticmethod
    def get_shape_pre_suffix(prefs, identifier):
        # Hack. prefs.get('box_shape') does not work before the value is once changed.
        if identifier == 'box_shape':
            return prefs.box_shape
        elif identifier == 'sphere_shape':
            return prefs.sphere_shape
        elif identifier == 'capsule_shape':
            return prefs.capsule_shape
        elif identifier == 'convex_shape':
            return prefs.convex_shape
        elif identifier == 'voxel_shape':
            return prefs.voxel_shape
        else:  # identifier == 'mesh_shape':
            return prefs.mesh_shape

    @staticmethod
    def force_redraw():
        """Hack to redraw UI"""
        bpy.context.space_data.overlay.show_text = not bpy.context.space_data.overlay.show_text
        bpy.context.space_data.overlay.show_text = not bpy.context.space_data.overlay.show_text
        pass

    def arm_navigation_timer(self):
        """Make sure poke_navigation_redraw() is scheduled. Only one timer
        is ever in flight - it re-arms itself via its own return value for
        as long as navigation_hold_until keeps getting pushed out, so this
        just needs to kick it off once."""
        if not self.navigation_timer_scheduled:
            self.navigation_timer_scheduled = True
            bpy.app.timers.register(self.poke_navigation_redraw, first_interval=NAVIGATION_HOLD_SECONDS)

    def poke_navigation_redraw(self):
        """bpy.app.timers callback: force a repaint once the navigation hold
        window elapses, even if no further event ever reaches modal() or
        draw_viewport_overlay() to notice on its own (e.g. the user stops
        touching mouse/keyboard right after navigating, and Blender doesn't
        repaint an idle viewport by itself).

        This deliberately does NOT set self.navigation directly - it only
        prompts a fresh repaint, and draw_viewport_overlay() re-derives the
        real answer from the live view_matrix each time it draws. That
        means this can never falsely clear the dimming while navigation is
        still genuinely in progress: if the view is still changing, Blender
        is already generating real repaints on its own, each of which
        pushes the hold window out again before this timer's turn comes.
        Re-arms itself via its return value, so only one timer is ever in
        flight.
        """
        try:
            remaining = self.navigation_hold_until - time.time()
            if remaining > 0:
                return remaining
            self.navigation_timer_scheduled = False
            self.navigation_area.tag_redraw()
        except ReferenceError:
            # operator has already finished/cancelled and its RNA was freed
            pass
        return None

    def arm_decimate_timer(self):
        """Make sure apply_decimate_value() runs once dragging pauses.
        Mirrors arm_navigation_timer(): only one timer is ever in flight -
        it re-arms itself for as long as decimate_debounce_until keeps
        getting pushed out by further MOUSEMOVE deltas, so this just needs
        to kick it off once."""
        if not self.decimate_timer_scheduled:
            self.decimate_timer_scheduled = True
            bpy.app.timers.register(self.poke_decimate_timer, first_interval=MODIFIER_DEBOUNCE_SECONDS)

    def poke_decimate_timer(self):
        """bpy.app.timers callback: apply the dragged decimate ratio once
        the debounce window elapses without a further MOUSEMOVE delta
        pushing it out again. Re-arms itself via its return value."""
        try:
            remaining = self.decimate_debounce_until - time.time()
            if remaining > 0:
                return remaining
            self.decimate_timer_scheduled = False
            self.apply_decimate_value(bpy.context)
        except ReferenceError:
            # operator has already finished/cancelled and its RNA was freed
            pass
        return None

    def apply_decimate_value(self, context):
        """Re-evaluate the Decimate modifiers at the currently dragged
        ratio. Forces a depsgraph evaluation per collider (via
        mod.face_count), so callers debounce this rather than calling it on
        every MOUSEMOVE delta."""
        dec_amount = self.current_settings_dic['decimate']
        # I had to iterate over all object because it crashed when just iterating over the modifiers.
        self.face_counts = []
        for obj in self.new_colliders_list:
            for mod in obj.modifiers:
                if mod in self.decimate_modifiers:
                    mod.ratio = dec_amount
                    self.face_counts.append(mod.face_count)

        self.report({'INFO'}, "Total collider face count:" + str(sum(self.face_counts)))
        self.draw_callback_px(context)

    def arm_remesh_timer(self):
        """Make sure apply_remesh_value() runs once dragging pauses. Same
        debounce pattern as arm_decimate_timer() / arm_navigation_timer()."""
        if not self.remesh_timer_scheduled:
            self.remesh_timer_scheduled = True
            bpy.app.timers.register(self.poke_remesh_timer, first_interval=MODIFIER_DEBOUNCE_SECONDS)

    def poke_remesh_timer(self):
        """bpy.app.timers callback: apply the dragged voxel size once the
        debounce window elapses without a further MOUSEMOVE delta pushing
        it out again. Re-arms itself via its return value."""
        try:
            remaining = self.remesh_debounce_until - time.time()
            if remaining > 0:
                return remaining
            self.remesh_timer_scheduled = False
            self.apply_remesh_value(bpy.context)
        except ReferenceError:
            # operator has already finished/cancelled and its RNA was freed
            pass
        return None

    def apply_remesh_value(self, context):
        """Re-evaluate the remesh result at the currently dragged voxel
        size multiplier. Base implementation just nudges the Remesh
        modifier's voxel_size (cheap - Blender's depsgraph re-evaluates it
        lazily on the next redraw). OBJECT_OT_add_bounding_simplified_mesh
        overrides this to rebuild its voxel grid via execute() instead,
        which is the actually slow path callers need debounced."""
        multiplier = self.current_settings_dic['voxel_size_multiplier']
        for mod, max_dim in self.remesh_data:
            mod.voxel_size = multiplier * max_dim

    def set_collisions_wire_preview(self, mode):
        """Show wireframe for colliders"""
        if mode in ['PREVIEW', 'ALWAYS']:
            for obj in self.new_colliders_list:
                obj.show_wire = True
        else:
            for obj in self.new_colliders_list:
                obj.show_wire = False

    @staticmethod
    def remove_objects(list):
        """Remove list of objects and their exclusively-owned mesh data."""
        ids = []
        for ob in list:
            if ob:
                try:
                    if isinstance(ob.data, bpy.types.Mesh) and ob.data.users == 1:
                        ids.append(ob.data)
                    ids.append(ob)
                except ReferenceError:
                    pass
        if ids:
            bpy.data.batch_remove(ids)

    @staticmethod
    def get_delta_value(delta, event, sensibility=0.05, tweak_amount=10, round_precision=0):
        """Get delta of input movement"""
        delta = delta * sensibility

        if event.ctrl:  # snap
            delta = round(delta, round_precision)
        if event.shift:  # tweak
            delta /= tweak_amount

        return delta

    @staticmethod
    def get_mesh_Edit(obj, use_modifiers=False):
        """ Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no
        vertices to return"""
        me = obj.data
        new_mesh = bpy.data.meshes.new('')

        if use_modifiers:  # self.my_use_modifier_stack == True
            # Bug: #249
            for mod in obj.modifiers:
                mod.show_on_cage = True
                mod.show_in_editmode = True
            me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (
            # adding, deleting, transforming)

            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            OBJECT_OT_add_bounding_object.merge_object_instances(bm, obj, depsgraph)

        else:  # use_modifiers == False
            # Get a BMesh representation
            me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (
            # adding, deleting, transforming)
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()

        vertices_select = [v for v in bm.verts if not v.select]
        bmesh.ops.delete(bm, geom=vertices_select)

        bm.verts.ensure_lookup_table()
        bm.to_mesh(new_mesh)

        if len(bm.faces) < 1:
            return None

        return new_mesh

    @staticmethod
    def get_edit_mode_vertices_local_space(obj, use_modifiers=False):
        """ Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no
        vertices to return"""
        me = obj.data

        # len(obj.modifiers) has to be bigger than 0. If there are no modifiers are assigned to the object the simple mesh can be used.
        # If len(obj.modifiers) == 0, the vertices are not selected and used_vertices is empty for some reason.
        if use_modifiers and len(obj.modifiers) > 0:
            # Get mesh information with the modifiers applied

            # Fix for Bug: #249
            for mod in obj.modifiers:
                mod.show_on_cage = True
                mod.show_in_editmode = True

            me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            OBJECT_OT_add_bounding_object.merge_object_instances(bm, obj, depsgraph)
            bm.verts.ensure_lookup_table()

        else:  # use_modifiers == False
            # Get a BMesh representation
            me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)
            bm = bmesh.from_edit_mesh(me)

        used_vertices = [v for v in bm.verts if v.select]
        if len(used_vertices) == 0:
            return None

        # This is needed for the bmesh not bo be destroyed, even if the variable isn't used later.
        OBJECT_OT_add_bounding_object.bmesh(bm)
        return used_vertices

    @staticmethod
    def get_object_mode_vertices_local_space(obj, use_modifiers=False):
        """ Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return """
        me = obj.data
        me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        if use_modifiers and len(obj.modifiers) > 0:
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            OBJECT_OT_add_bounding_object.merge_object_instances(bm, obj, depsgraph)
            bm.verts.ensure_lookup_table()
            used_vertices = bm.verts

            # This is needed for the bmesh not bo be destroyed, even if the variable isn't used later.
            OBJECT_OT_add_bounding_object.bmesh(bm)

        else:
            # Get a BMesh representation
            used_vertices = me.vertices

        if len(used_vertices) == 0:
            return None

        return used_vertices

    @staticmethod
    def transform_vertex_space(vertex_co, obj):
        # iterate over vertex coordinates to transform the positions to the appropriate space
        ws_vertex_co = []
        for i in range(len(vertex_co)):
            co = vertex_co[i]
            ws_vertex_co.append(obj.matrix_world.inverted() @ co)

        return ws_vertex_co

    @staticmethod
    def get_vertex_coordinates(obj, space, used_vertices):
        """ returns vertex and face information for the bounding box based on the given coordinate space (e.g., world or local)"""

        # Modify the BMesh, can do anything here...
        co = []

        if space == 'GLOBAL':
            # get world space coordinates of the vertices
            for v in used_vertices:
                v_local = v
                v_global = obj.matrix_world @ v_local.co

                co.append(v_global)

        else:  # space == 'LOCAL'
            for v in used_vertices:
                co.append(v.co)

        return co

    @staticmethod
    def merge_object_instances(bm, obj, depsgraph):
        """Merge geometry-node / particle / dupli instances generated by obj's
        modifier stack into bm, in obj's local space.

        bmesh.from_object()/to_mesh() only capture an object's own real mesh
        data - they silently drop unrealized instances produced by e.g. a
        Geometry Nodes "Instance on Points" node without a "Realize Instances"
        node downstream. depsgraph.object_instances is the API that enumerates
        that generated geometry, so it is walked here and merged manually.
        """
        obj_matrix_inv = obj.matrix_world.inverted()

        for inst in depsgraph.object_instances:
            if not inst.is_instance:
                continue
            if inst.parent is None or inst.parent.original != obj:
                continue

            inst_obj = inst.object
            if inst_obj.type not in VALID_OBJECT_TYPES:
                continue  # skip lights, empties, etc. gracefully

            try:
                inst_mesh = inst_obj.to_mesh()
            except RuntimeError:
                continue

            if inst_mesh is None:
                continue
            if not inst_mesh.polygons and not inst_mesh.edges and not inst_mesh.vertices:
                inst_obj.to_mesh_clear()
                continue

            local_matrix = obj_matrix_inv @ inst.matrix_world
            inst_mesh.transform(local_matrix)
            bm.from_mesh(inst_mesh)
            inst_obj.to_mesh_clear()

    @staticmethod
    def mesh_from_selection(obj, use_modifiers=False):
        mesh = obj.data.copy()
        mesh.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        bm = bmesh.new()

        if use_modifiers:
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            OBJECT_OT_add_bounding_object.merge_object_instances(bm, obj, depsgraph)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        else:  # self.my_use_modifier_stack == False:
            bm.from_mesh(mesh)

        bm.to_mesh(mesh)
        bm.free()

        return mesh

    def is_valid_object(self, obj):
        """Is the object valid to be used as a base mesh for collider generation"""
        if obj is None or obj.type not in VALID_OBJECT_TYPES:
            return False
        return True

    @staticmethod
    def create_collection(context, collection_name):
        """Find or create a collider collection as a direct, local child of
        context.scene's root collection. Each scene keeps its own
        collection - never one shared/reused across scenes - and
        library-linked collections are ignored."""
        root = context.scene.collection
        collection = _local_child_collection(root, collection_name)
        if collection is None:
            collection = bpy.data.collections.new(_next_available_local_name(collection_name))
            root.children.link(collection)

        return collection

    # Collections
    @classmethod
    def add_to_collections(cls, context, obj, collection_name, hide=False, color='NONE'):
        col = cls.create_collection(context, collection_name)
        if hide:
            col.hide_viewport = True
            prefs = bpy.context.preferences.addons[base_package].preferences
            if prefs.hide_render_on_creation:
                col.hide_render = True
        try:
            col.objects.link(obj)
        except RuntimeError as err:
            pass
        col.color_tag = color

        return col

    @staticmethod
    def remove_empty_collection(context, collection_name):
        collection = _local_child_collection(context.scene.collection, collection_name)
        if collection is not None and len(collection.objects) == 0:
            bpy.data.collections.remove(collection)

    def _clear_modifier_bake_cache(self):
        """Free the mesh datablocks cached by convert_to_mesh() /
        apply_all_modifiers() (see self._modifier_bake_cache). They're kept
        alive only by this dict - never linked to any object - so they must
        be removed explicitly on confirm/cancel or they'd leak as orphan
        mesh data."""
        cache = getattr(self, '_modifier_bake_cache', None)
        if not cache:
            return
        meshes = [me for me in cache.values() if me and me.name in bpy.data.meshes]
        if meshes:
            bpy.data.batch_remove(meshes)
        self._modifier_bake_cache = {}

    @staticmethod
    def set_collections(obj, collections):
        """link an object to a collection"""
        old_collection = obj.users_collection

        for col in collections:
            try:
                col.objects.link(obj)
            except RuntimeError:
                pass

        for col in old_collection:
            if col not in collections:
                col.objects.unlink(obj)

    # Modifiers
    def apply_all_modifiers(self, context, obj, cache_key=None):
        """Replace obj's mesh data with the fully evaluated result of its
        modifier stack - including any unrealized instances a modifier like
        Geometry Nodes "Instance on Points" produces without a "Realize
        Instances" node - then clear the modifiers.

        bpy.ops.object.modifier_apply() applied per-modifier fails outright
        ("Evaluated geometry from modifier does not contain a mesh") once a
        modifier's output is instances-only, since Blender's built-in Apply
        can't bake unrealized instances into real geometry. Evaluating via
        the depsgraph and merging instances manually (merge_object_instances)
        sidesteps that limitation.

        `cache_key`, if given, reuses/populates self._modifier_bake_cache so
        repeated calls for the same source object (e.g. once per MOUSEMOVE
        delta while dragging) don't each pay for a fresh depsgraph
        evaluation - see convert_to_mesh() for why that matters (#631).
        """
        context.view_layer.objects.active = obj
        if not obj.modifiers:
            return

        cached_mesh = self._modifier_bake_cache.get(cache_key) if cache_key else None
        if cached_mesh is not None and cached_mesh.name in bpy.data.meshes:
            old_data = obj.data
            obj.data = cached_mesh.copy()
            obj.modifiers.clear()
            if old_data.users == 0:
                bpy.data.meshes.remove(old_data)
            return

        depsgraph = context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)

        bm = bmesh.new()
        bm.from_mesh(me)
        self.merge_object_instances(bm, obj, depsgraph)
        bm.to_mesh(me)
        bm.free()

        old_data = obj.data
        obj.data = me
        obj.modifiers.clear()

        if old_data.users == 0:
            bpy.data.meshes.remove(old_data)

        if cache_key:
            self._modifier_bake_cache[cache_key] = me.copy()

    @staticmethod
    def remove_all_modifiers(context, obj):
        """Remove all modifiers of an object"""
        context.view_layer.objects.active = obj
        if obj:
            for mod in obj.modifiers:
                obj.modifiers.remove(mod)

    @staticmethod
    def del_displace_modifier(bounding_object):
        """Delete displace modifiers called 'Collider_displace'"""
        if bounding_object:
            if bounding_object.modifiers.get('Collider_displace'):
                mod = bounding_object.modifiers['Collider_displace']
                bounding_object.modifiers.remove(mod)

    @staticmethod
    def del_decimate_modifier(bounding_object):
        """Delete modifiers called 'Collider_decimate'"""
        if bounding_object:
            if bounding_object.modifiers.get(DECIMATE_NAME):
                mod = bounding_object.modifiers[DECIMATE_NAME]
                bounding_object.modifiers.remove(mod)

    # Time classes
    @staticmethod
    def print_generation_time(shape, time):
        print(shape)
        print("Time elapsed: ", str(time))

    @staticmethod
    def store_initial_obj_state(obj, collections):
        dic = {}
        dic['obj'] = obj
        col_list = [col.name for col in collections]
        dic['users_collection'] = col_list

        return dic

    @staticmethod
    def store_obj_mod_in_dic(object):
        mods = []

        for mod in object.modifiers:
            mods.append({"mod": mod, "show_viewport": mod.show_viewport, "show_in_editmode": mod.show_in_editmode})

        return mods

    @staticmethod
    def restore_obj_mod_from_dic(modifier_dic):
        for mod_entry in modifier_dic:
            modifier = mod_entry["mod"]
            modifier.show_viewport = mod_entry["show_viewport"]
            modifier.show_in_editmode = mod_entry["show_in_editmode"]

    def convert_to_mesh(self, context, object, use_modifiers=False):
        # Baking (evaluated_depsgraph_get + new_from_object) is only needed
        # for use_modifiers=True - the base object's modifier stack doesn't
        # change between drag deltas, so reuse the last bake instead of
        # re-evaluating the whole scene's depsgraph on every MOUSEMOVE (#631).
        cache_key = (object, use_modifiers) if use_modifiers else None
        cached_mesh = self._modifier_bake_cache.get(cache_key) if cache_key else None

        if cached_mesh is not None and cached_mesh.name in bpy.data.meshes:
            me = cached_mesh.copy()
        else:
            mods = self.store_obj_mod_in_dic(object)

            for mod in object.modifiers:
                mod.show_viewport = use_modifiers
                mod.show_in_editmode = use_modifiers

            if use_modifiers:
                deg = context.evaluated_depsgraph_get()
                me = bpy.data.meshes.new_from_object(object.evaluated_get(deg), depsgraph=deg)

                bm = bmesh.new()
                bm.from_mesh(me)
                self.merge_object_instances(bm, object, deg)
                bm.to_mesh(me)
                bm.free()
            else:
                # Create mesh from base data without applying modifiers
                me = object.data.copy()
                me.update()

            self.restore_obj_mod_from_dic(mods)

            if cache_key:
                self._modifier_bake_cache[cache_key] = me.copy()

        new_obj = bpy.data.objects.new(object.name + "_mesh", me)
        col = self.add_to_collections(context, new_obj, 'tmp_mesh', hide=False, color=self.prefs.col_tmp_collection_color)

        new_obj.matrix_world = object.matrix_world
        context.view_layer.objects.active = new_obj
        return new_obj

    def primitive_postprocessing(self, context, bounding_object, base_object_collections):
        self.set_object_collider_group(bounding_object)

        self.set_viewport_drawing(context, bounding_object)
        if self.use_weld_modifier:
            add_weld_modifier(context, bounding_object)

        self.add_displacement_modifier(context, bounding_object)
        self.set_collections(bounding_object, base_object_collections)

        if self.prefs.use_col_collection:
            collection_name = self.prefs.col_collection_name
            self.add_to_collections(context, bounding_object, collection_name, color=self.prefs.col_collection_color)

        if self.use_remesh:
            self.add_remesh_modifier(context, bounding_object)

        if self.use_decimation:
            self.add_decimate_modifier(context, bounding_object)

        if self.use_geo_nodes_hull:
            if bpy.app.version >= (3, 2, 0):
                self.add_geo_nodes_hull(bounding_object)
            else:
                print("Update to a newer Blender Version to access all addon features")

        if not self.prefs.use_parent_to:
            mtx = bounding_object.matrix_world
            bounding_object.parent = None
            bounding_object.matrix_world = mtx

        prefs = bpy.context.preferences.addons[base_package].preferences
        if context.scene.active_physics_material:
            mat_name = context.scene.active_physics_material.name
        elif prefs.physics_material_name:
            mat_name = prefs.physics_material_name
            mat = create_default_material()
            if mat:
                set_active_physics_material(context, mat.name)
        else:
            mat_name = ''

        if self.use_keep_original_materials == False or self.keep_original_material == False:
            assign_physics_material(bounding_object, mat_name)

        bounding_object['isCollider'] = True
        bounding_object['collider_group'] = self.collision_groups[self.collision_group_idx].mode
        bounding_object['collider_shape'] = self.shape

        if self.prefs.wireframe_mode in ['PREVIEW', 'ALWAYS']:
            bounding_object.show_wire = True
        else:
            bounding_object.show_wire = False

    def get_pre_processed_mesh_objs(self, context, default_world_spc=True, use_local=False, local_world_spc=False,
                                    use_mesh_copy=False, add_to_tmp_meshes=True):

        objs = []

        # Create the bounding geometry, depending on edit or object mode.
        for base_ob in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(base_ob):
                continue

            if base_ob and base_ob.type in VALID_OBJECT_TYPES:
                user_collections = base_ob.users_collection
                if base_ob.type == 'MESH':
                    obj = base_ob.copy() if use_mesh_copy else base_ob
                    obj.data = base_ob.data.copy() if use_mesh_copy else base_ob.data
                else:
                    # store initial state for operation cancel
                    self.original_obj_data.append(self.store_initial_obj_state(base_ob, user_collections))
                    # convert meshes
                    obj = self.convert_to_mesh(context, base_ob, use_modifiers=self.my_use_modifier_stack)
                    if add_to_tmp_meshes:
                        self.tmp_meshes.append(obj)

                creation_mode = self.creation_mode[
                    self.creation_mode_idx] if self.obj_mode == 'OBJECT' else self.creation_mode_edit[
                    self.creation_mode_idx]

                # Temp meshes for Loose islands
                if self.use_loose_mesh:

                    base = obj

                    bpy.context.view_layer.objects.active = obj

                    tmp_ob = obj.copy()
                    tmp_ob.data = obj.data.copy()
                    col = self.add_to_collections(context, tmp_ob, 'tmp_mesh', hide=False,
                                                  color=self.prefs.col_tmp_collection_color)

                    if self.obj_mode == 'EDIT':
                        tmp_ob = delete_non_selected_verts(tmp_ob)

                    if self.my_use_modifier_stack:
                        self.apply_all_modifiers(context, tmp_ob, cache_key=(base_ob, True))
                    base = tmp_ob

                    self.tmp_meshes.append(tmp_ob)

                    if use_local and self.my_space == 'LOCAL':
                        split_objs = create_objs_from_island(base, use_world=local_world_spc)
                    else:
                        split_objs = create_objs_from_island(base, use_world=default_world_spc)

                    for split in split_objs:
                        col = self.add_to_collections(context, split, 'tmp_mesh', hide=False,
                                                      color=self.prefs.col_tmp_collection_color)
                        col.color_tag = self.prefs.col_tmp_collection_color

                        for mat in base_ob.material_slots:
                            set_material(split, mat.material)

                        objs.append((base_ob, split))

                    if add_to_tmp_meshes:
                        self.tmp_meshes.extend(split_objs)

                    if self.use_modifier_stack and self.my_use_modifier_stack:
                        list = [tmp_ob]
                        self.remove_objects(list)
                else:
                    objs.append((base_ob, obj))

        return objs

    def set_viewport_drawing(self, context, bounding_object):
        """ Assign material to the bounding object and set the visibility settings of the created object."""
        if context.space_data.shading.type != 'SOLID':
            context.space_data.shading.type = 'SOLID'
        else:
            col = self.collision_groups[self.collision_group_idx].color
            set_object_color(bounding_object, (col[0], col[1], col[2], self.current_settings_dic['alpha']))

    def set_object_collider_group(self, obj):
        # user idx rather than name for the property, so that renaming is possible.
        obj['collider_group'] = self.collision_groups[self.collision_group_idx].mode

    def set_collider_name(self, new_collider, parent_name):
        basename = parent_name
        prefs = self.prefs

        # Ignore rigid body in base_name
        if prefs.rigid_body_extension:
            if prefs.rigid_body_naming_position == 'SUFFIX':
                end = prefs.rigid_body_separator + prefs.rigid_body_extension

                if basename.endswith(end):
                    basename = basename[:-(len(end))]

            else:
                start = prefs.rigid_body_extension + prefs.rigid_body_separator
                if basename.startswith(start):
                    basename = basename[len(start):]

        new_name = self.collider_name(basename=basename)

        new_collider.name = new_name
        self.set_data_name(new_collider, new_name, self.data_suffix)

    def update_names(self):
        self._naming_cache = {}
        for obj in self.new_colliders_list:
            new_name = self.collider_name(basename=self.basename, exclude=obj.name)
            if new_name == obj.name:
                continue
            obj.name = new_name
            self.set_data_name(obj, new_name, self.data_suffix)

    def reset_to_initial_state(self, context):
        for obj in bpy.data.objects:
            obj.select_set(False)
        for obj in self.selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode=self.obj_mode)

        # Hide all temp meshes exactly once, here, rather than inside
        # primitive_postprocessing().  The old placement ran N times with N
        # objects in self.tmp_meshes → O(N²) hide_set() calls for N islands.
        for obj in self.tmp_meshes:
            try:
                obj.hide_set(True)
            except Exception:
                pass

    def add_displacement_modifier(self, context, bounding_object):
        # add displacement modifier and safe it to manipulate the strength in the modal operator
        modifier = bounding_object.modifiers.new(name="Collider_displace", type='DISPLACE')
        modifier.strength = self.current_settings_dic['displace_offset']

        self.displace_modifiers.append(modifier)

    def add_remesh_modifier(self, context, bounding_object):
        # add decimation modifier and safe it to manipulate the strength in the modal operator
        modifier = bounding_object.modifiers.new(name="Collider_remesh", type='REMESH')
        modifier.mode = 'VOXEL'
        max_dim = self.get_object_max_dimension(bounding_object)
        modifier.voxel_size = self.current_settings_dic['voxel_size_multiplier'] * max_dim
        self.remesh_modifiers.append(modifier)
        self.remesh_data.append((modifier, max_dim))

    def add_decimate_modifier(self, context, bounding_object):
        # add decimation modifier and safe it to manipulate the strength in the modal operator
        modifier = bounding_object.modifiers.new(name=DECIMATE_NAME, type='DECIMATE')
        modifier.ratio = self.current_settings_dic['decimate']
        self.decimate_modifiers.append(modifier)

    def add_geo_nodes_hull(self, bounding_object):

        if bpy.data.node_groups.get('Convex_Hull'):
            group = bpy.data.node_groups['Convex_Hull']

        else:  # Create Convex Hull Geometry Node Setup
            group = geometry_node_group_empty_new()
            nodes = group.nodes

            geom_in = nodes.get('Group Input')
            geom_out = nodes.get('Group Output')
            hull_node = nodes.new('GeometryNodeConvexHull')

            group.links.new(geom_in.outputs[0], hull_node.inputs[0])
            group.links.new(hull_node.outputs[0], geom_out.inputs[0])

        modifier = bounding_object.modifiers.new(name="Convex_Hull", type='NODES')
        modifier.node_group = group

    def get_time_elapsed(self):
        t1 = time.time() - self.t0
        return t1

    def reset_display(self, context):
        context.space_data.shading.color_type = self.original_color_type
        context.space_data.shading.type = self.original_shading_type

    def cancel_cleanup(self, context, delete_colliders=True):
        if delete_colliders:
            # Remove previously created collisions
            self.remove_objects(self.new_colliders_list)

        # Delete temporary objects
        self.remove_objects(self.tmp_meshes)
        self.remove_empty_collection(context, 'tmp_mesh')
        self._clear_modifier_bake_cache()

        self.reset_display(context)

        # execute() normally restores the starting selection/active object/mode
        # via reset_to_initial_state() at its own end. If generation is
        # cancelled or raises before that point is reached, none of that ever
        # runs, so the user can be left stranded in Object Mode after starting
        # in Edit Mode. Restore it explicitly here as a guarantee.
        for obj in bpy.data.objects:
            obj.select_set(False)
        for obj in self.selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = self.active_obj
        if context.object and context.object.mode != self.obj_mode:
            bpy.ops.object.mode_set(mode=self.obj_mode)

        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        except ValueError:
            pass

    def join_primitives(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        last_selected = None

        for obj in self.new_colliders_list:
            if obj:
                obj.select_set(True)
                context.view_layer.objects.active = self.new_colliders_list[0]
                last_selected = obj

        bpy.ops.object.join()
        new_collider = self.new_colliders_list[0]
        self.new_colliders_list = [new_collider]
        return new_collider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # has to be in --init

        # operator settings
        self.is_mesh_to_collider = False

        # modal settings
        self.use_decimation = False
        self.use_geo_nodes_hull = False
        self.use_cylinder_segments = False
        self.use_modifier_stack = False
        self.use_weld_modifier = False
        self.use_space = False
        self.use_cylinder_axis = False
        self.use_capsule_axis = False
        self.use_capsule_segments = False
        self.use_global_local_switches = False
        self.use_sphere_segments = False
        self.use_shape_change = True
        self.use_creation_mode = True
        self.collider_groups_enabled = False
        self.use_keep_original_materials = False
        self.use_keep_original_name = False
        self.use_remesh = False
        self.use_height_multiplier = False
        self.use_width_multiplier = False
        self.use_diagonal_fill = False

        self.remesh_data = []

        # default shape init
        self.shape = ''

        # UI/UX
        self.ignore_input = False

        self.use_recenter_origin = False
        self.debug_parenting_off = False
        self.use_custom_rotation = False

        self.collision_group_idx = 0
        self._naming_cache = {}

        # Modifier-stack bake results (convert_to_mesh / apply_all_modifiers),
        # keyed by (base_ob, use_modifiers). Baking involves an
        # evaluated_depsgraph_get() + new_from_object(), which in scenes with
        # many other objects/modifiers costs tens to hundreds of ms - and
        # execute() (hence this bake) reruns on every MOUSEMOVE delta while
        # dragging the collider's own parameters, even though the base
        # object's own modifier stack doesn't change during that drag. Caching
        # the baked mesh here turns that into a one-time cost per base object
        # for the operator's lifetime (#631). Cleared in
        # _clear_modifier_bake_cache() on confirm/cancel.
        self._modifier_bake_cache = {}

    @classmethod
    def poll(cls, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type in VALID_OBJECT_TYPES:
                count = count + 1
        return count > 0

    # Order in which get_active_numeric_field() checks the *_active flags.
    # At most one is ever True at a time - see set_modal_state().
    _NUMERIC_FIELDS = (
        'displace_active', 'decimate_active', 'opacity_active',
        'cylinder_segments_active', 'sphere_segments_active', 'capsule_segments_active',
        'height_active', 'width_active', 'remesh_active',
    )

    def get_active_numeric_field(self):
        """Name of the *_active flag currently active for mouse-drag, if
        any - the field direct numeric text entry (issue #640) would apply
        to if the user started typing right now."""
        for name in self._NUMERIC_FIELDS:
            if getattr(self, name):
                return name
        return None

    @staticmethod
    def _numeric_char_for_event(event):
        """Character a key event contributes to numeric text entry
        ('0'-'9', '.', '-'), or '' if it isn't one. Prefers event.ascii,
        which already accounts for keyboard layout/shift state; falls back
        to the physical key for the numpad, where ascii isn't reliably
        populated the same way across platforms."""
        if event.ascii and event.ascii in '0123456789.-':
            return event.ascii
        return {
            'NUMPAD_0': '0', 'NUMPAD_1': '1', 'NUMPAD_2': '2', 'NUMPAD_3': '3', 'NUMPAD_4': '4',
            'NUMPAD_5': '5', 'NUMPAD_6': '6', 'NUMPAD_7': '7', 'NUMPAD_8': '8', 'NUMPAD_9': '9',
            'NUMPAD_PERIOD': '.', 'NUMPAD_MINUS': '-',
        }.get(event.type, '')

    def start_numeric_input(self, field, first_char):
        """Begin direct numeric text entry for `field` (issue #640), seeded
        with the character that triggered it."""
        self.numeric_input_active = True
        self.numeric_input_field = field
        self.numeric_input_str = first_char
        self.force_redraw()

    def handle_numeric_input(self, context, event):
        """Handle a key event while direct numeric text entry (started by
        start_numeric_input) is in progress. Takes over the keys that
        normally finish/cancel the operator (RET/NUMPAD_ENTER, ESC) so they
        confirm/cancel the typed number instead, and swallows every other
        event - including MOUSEMOVE and subclasses' own hotkeys - so
        nothing else can interfere with the value being typed."""
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            # a hard cancel of the whole operator still works while typing
            self.cancel_numeric_input(event)
            self.cancel_cleanup(context)
            return {'CANCELLED'}

        if event.value != 'PRESS':
            return {'RUNNING_MODAL'}

        if event.type in {'RET', 'NUMPAD_ENTER'}:
            self.confirm_numeric_input(context, event)
        elif event.type == 'ESC':
            self.cancel_numeric_input(event)
        elif event.type == 'BACK_SPACE':
            if self.numeric_input_str:
                self.numeric_input_str = self.numeric_input_str[:-1]
                self.force_redraw()
            else:
                self.cancel_numeric_input(event)
        else:
            char = self._numeric_char_for_event(event)
            if char == '-':
                # toggle sign, matching Blender's own numeric input, rather
                # than only accepting '-' as the very first character typed
                if self.numeric_input_str.startswith('-'):
                    self.numeric_input_str = self.numeric_input_str[1:]
                else:
                    self.numeric_input_str = '-' + self.numeric_input_str
                self.force_redraw()
            elif char == '.' and '.' not in self.numeric_input_str:
                self.numeric_input_str += '.'
                self.force_redraw()
            elif char.isdigit():
                self.numeric_input_str += char
                self.force_redraw()

        return {'RUNNING_MODAL'}

    def confirm_numeric_input(self, context, event):
        """Apply the typed buffer to the field entry was started for, then
        hand control back to mouse-drag for that same field."""
        field = self.numeric_input_field
        text = self.numeric_input_str
        self.numeric_input_active = False
        self.numeric_input_str = ''
        self.numeric_input_field = None

        try:
            value = float(text)
        except ValueError:
            value = None

        if value is not None:
            self.apply_numeric_value(context, field, value)
        elif text:
            self.report({'WARNING'}, f"Ignored invalid numeric input: '{text}'")

        # avoid a mouse-drag jump on the next MOUSEMOVE: re-baseline against
        # wherever the mouse is now, exactly like the LEFT_ALT-release and
        # LEFT_SHIFT/LEFT_CTRL handlers below already do.
        self.ref_settings_dic = self.current_settings_dic.copy()
        self.mouse_initial_x = event.mouse_x
        self.mouse_position = [event.mouse_x, event.mouse_y]
        self.force_redraw()

    def cancel_numeric_input(self, event):
        """Abort in-progress typing without applying it, handing control
        back to mouse-drag for the field entry was started for."""
        self.numeric_input_active = False
        self.numeric_input_str = ''
        self.numeric_input_field = None

        self.ref_settings_dic = self.current_settings_dic.copy()
        self.mouse_initial_x = event.mouse_x
        self.mouse_position = [event.mouse_x, event.mouse_y]
        self.force_redraw()

    def apply_numeric_value(self, context, field, value):
        """Apply a typed numeric value (see confirm_numeric_input) to
        `field`, mirroring the equivalent MOUSEMOVE drag handling below."""
        if field == 'displace_active':
            strength = value
            for mod in self.displace_modifiers:
                mod.strength = strength
                mod.show_on_cage = True
                mod.show_in_editmode = True
            self.current_settings_dic['displace_offset'] = strength

        elif field == 'decimate_active':
            dec_amount = numpy.clip(value, 0.01, 1.0)
            if self.current_settings_dic['decimate'] != dec_amount:
                self.current_settings_dic['decimate'] = dec_amount
                # A one-shot typed confirm can afford the same immediate
                # evaluation a continuous drag can't (see apply_decimate_value).
                self.apply_decimate_value(context)

        elif field == 'opacity_active':
            if self.shading_modes[self.shading_idx] == 'OBJECT':
                color_alpha = numpy.clip(value, 0.0, 1.0)
                for obj in self.new_colliders_list:
                    obj.color[3] = color_alpha
                self.prefs.user_groups_alpha = color_alpha
                self.current_settings_dic['alpha'] = color_alpha

        elif field == 'cylinder_segments_active':
            segment_count = max(3, int(round(value)))
            if segment_count != int(round(self.current_settings_dic['cylinder_segments'])):
                self.current_settings_dic['cylinder_segments'] = segment_count
                self.execute(context)

        elif field == 'height_active':
            height_mult = numpy.clip(value, 0, 10.0)
            if self.current_settings_dic['height_mult'] != height_mult:
                self.current_settings_dic['height_mult'] = height_mult
                self.execute(context)

        elif field == 'width_active':
            width_mult = numpy.clip(value, 0, 10.0)
            if self.current_settings_dic['width_mult'] != width_mult:
                self.current_settings_dic['width_mult'] = width_mult
                self.execute(context)

        elif field == 'sphere_segments_active':
            segments = max(2, int(round(value)))
            if segments != int(round(self.current_settings_dic['sphere_segments'])):
                self.current_settings_dic['sphere_segments'] = segments
                self.execute(context)

        elif field == 'capsule_segments_active':
            segments = max(2, int(round(value)))
            if segments != int(round(self.current_settings_dic['capsule_segments'])):
                self.current_settings_dic['capsule_segments'] = segments
                self.execute(context)

        elif field == 'remesh_active':
            # Full re-execute (rather than mirroring the MOUSEMOVE handler's
            # direct mod.voxel_size tweak) since some shapes (e.g. Simplified
            # Mesh) rebuild the collider mesh manually from the multiplier
            # instead of adjusting a live Remesh modifier. A one-shot typed
            # confirm can afford the heavier call that a continuous drag
            # cannot.
            multiplier = numpy.clip(value, 0.001, 1.0)
            if self.current_settings_dic['voxel_size_multiplier'] != multiplier:
                self.current_settings_dic['voxel_size_multiplier'] = multiplier
                self.execute(context)

    def format_modal_value(self, active, value, is_int=False):
        """Format a modal-adjustable value for the HUD: the live typed
        buffer while direct numeric entry (issue #640) is in progress for
        this field, otherwise the regular mouse-drag formatted value."""
        if active and self.numeric_input_active:
            return self.numeric_input_str + '_'
        if is_int:
            return str(value)
        return '{value:.3f}'.format(value=value)

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):

        # Switching (or clearing) which field is active drops any in-progress
        # typed entry (issue #640) - its buffer was never applied to
        # current_settings_dic, so there is nothing to preserve.
        self.numeric_input_active = False
        self.numeric_input_str = ''
        self.numeric_input_field = None

        self.cylinder_segments_active = cylinder_segments_active
        self.displace_active = displace_active
        self.decimate_active = decimate_active
        self.opacity_active = opacity_active
        self.sphere_segments_active = sphere_segments_active
        self.capsule_segments_active = capsule_segments_active
        self.remesh_active = remesh_active
        self.height_active = height_active
        self.width_active = width_active

        # A keypress alone doesn't make Blender repaint the viewport (only
        # mouse motion over the region does), so the new highlight color set
        # above wouldn't show up until the next MOUSEMOVE. Force a repaint
        # now so activating a parameter highlights it immediately.
        self.force_redraw()

    def invoke(self, context, event):
        colSettings = context.scene.simple_collider

        self.collider_groups = [colSettings.visibility_toggle_user_group_01,
                                colSettings.visibility_toggle_user_group_02,
                                colSettings.visibility_toggle_user_group_03]

        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

        # get collision suffix from preferences
        self.prefs = context.preferences.addons[base_package].preferences

        # Active object
        if context.object is None:
            context.view_layer.objects.active = context.selected_objects[0]
        context.object.select_set(True)

        # INITIAL STATE
        self.navigation = False
        self.navigation_hold_until = 0.0  # grace window keeping navigation coloring on after the view last changed
        self.navigation_timer_scheduled = False
        self.navigation_area = context.area
        self.navigation_view_snapshot = None  # (view_matrix, view_distance) as of the last draw call
        self.selected_objects = context.selected_objects.copy()
        self.active_obj = context.view_layer.objects.active
        self.obj_mode = context.object.mode
        self.data_suffix = "_data"
        self.valid_input_selection = True

        self.collider_shapes_idx = 3
        self.collider_shapes = ['box_shape', 'sphere_shape', 'capsule_shape', 'convex_shape',
                                'mesh_shape', 'voxel_shape']

        # General init settings
        self.new_colliders_list = []
        self.tmp_meshes = []
        self.col_rotation_matrix_list = []
        self.col_center_loc_list = []

        self.name_count = 0

        # Mouse
        self.mouse_initial_x = event.mouse_x
        self.mouse_position = [event.mouse_x, event.mouse_y]
        self.my_space = colSettings.default_space

        # Decimate face count display
        # self.face_countall = 0
        self.face_counts = []
        self.face_countall = 0

        # Modal Settings
        self.my_use_modifier_stack = colSettings.default_modifier_stack
        self.x_ray = context.space_data.shading.show_xray

        # Modal Bools
        self.join_primitives = colSettings.default_join_primitives
        self.use_loose_mesh = colSettings.default_use_loose_island

        # Modal MODIFIERS
        self.remesh_active = False
        self.remesh_modifiers = []
        self.remesh_data = []
        # Debounce state for the voxel-size re-evaluation while dragging,
        # see arm_remesh_timer().
        self.remesh_debounce_until = 0.0
        self.remesh_timer_scheduled = False

        self.height_active = False
        self.width_active = False

        # Displace
        self.displace_active = False
        self.displace_modifiers = []

        # Decimate
        self.decimate_active = False
        self.decimate_modifiers = []
        # Debounce state for the decimate-ratio re-evaluation while
        # dragging, see arm_decimate_timer().
        self.decimate_debounce_until = 0.0
        self.decimate_timer_scheduled = False

        # Opacity
        self.opacity_active = False
        self.opacity_ref = 0.5

        # Sphere and Cylinder specific settings
        self.cylinder_axis = colSettings.default_cylinder_axis
        self.cylinder_segments_active = False
        self.sphere_segments_active = False
        self.capsule_segments_active = False

        # Direct numeric text entry (issue #640): once a field above is made
        # active via its hotkey, typing a digit/./- switches it from
        # mouse-drag to typed entry. See get_active_numeric_field(),
        # start_numeric_input() and handle_numeric_input().
        self.numeric_input_active = False
        self.numeric_input_str = ''
        self.numeric_input_field = None

        # Display settings
        self.color_type = context.space_data.shading.color_type
        self.original_color_type = context.space_data.shading.color_type
        self.original_shading_type = context.space_data.shading.type
        # Set up scene
        if context.space_data.shading.type == 'SOLID':
            context.space_data.shading.color_type = colSettings.default_color_type

        self.color_type = colSettings.default_color_type
        self.shading_idx = 0
        self.shading_modes = ['OBJECT', 'MATERIAL', 'SINGLE']

        self.creation_mode = ['INDIVIDUAL', 'SELECTION']

        self.creation_mode_edit = ['INDIVIDUAL', 'SELECTION']

        self.creation_mode_idx = self.creation_mode.index(colSettings.default_creation_mode)

        # Should physic materials be assigned or not.
        self.keep_original_material = colSettings.default_keep_original_material
        self.keep_original_name = colSettings.default_keep_original_name

        self.collider_groups_enabled = self.prefs.collider_groups_enabled
        self.collision_groups = self.collider_groups
        self.collision_group_idx = self.collision_groups.index(colSettings.visibility_toggle_user_group_01)

        # Object to Collider
        self.original_obj_data = []

        # display settings
        self.is_solidmode = True if context.space_data.shading.type == 'SOLID' else False

        default_alpha = 0.5
        default_decimate = 1.0
        default_offset = 0
        default_height_mult = 1
        default_width_mult = 1

        dict = collision_dictionary(default_alpha, default_offset, default_decimate,
                                    colSettings.default_sphere_segments,
                                    colSettings.default_cylinder_segments, colSettings.default_capsule_segments,
                                    colSettings.default_voxel_size, default_height_mult, default_width_mult)
        self.current_settings_dic = dict.copy()
        self.ref_settings_dic = dict.copy()

        # the arguments we pass to the callback
        args = (self, context)
        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        # self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_viewport_overlay, args, 'WINDOW', 'POST_PIXEL')
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_viewport_overlay, args, 'WINDOW', 'POST_PIXEL')

        # add modal handler
        context.window_manager.modal_handler_add(self)

        # stored for decimate display
        self.mouse_path = []

        try:
            self.execute(context)
        except Exception as ex:
            # If the initial generation fails, the draw handler and modal
            # handler added above would otherwise outlive this operator
            # instance. The viewport overlay callback keeps a reference to
            # `self`, so once Blender frees this operator's RNA struct the
            # next redraw raises a ReferenceError from draw_viewport_overlay.
            self.cancel_cleanup(context)
            self.report({'ERROR'}, f"Failed to generate collider: {ex}")
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        colSettings = context.scene.simple_collider

        # Ignore if Alt is pressed
        if event.alt:
            self.ignore_input = True
            self.force_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            # Whether the view is actually navigating is now detected in
            # draw_viewport_overlay() by watching the region's view_matrix
            # (see there for why: this handler doesn't reliably see events
            # for the duration of an MMB orbit drag at all, since Blender's
            # own view3d.rotate modal operator consumes them). This branch
            # only needs to cancel any in-progress parameter drag so
            # navigating doesn't fight with an active (S)/(D)/(A)/etc. edit.
            self.set_modal_state()
            return {'PASS_THROUGH'}

        # Direct numeric text entry (issue #640): once a field is active for
        # mouse-drag (S/D/A/E/H/W/R below), typing a digit/./- switches it to
        # typed entry instead. Handled ahead of the generic RET/ESC/
        # BACK_SPACE bindings below so those keys edit the typed number
        # while entry is in progress, rather than finishing/cancelling the
        # whole operator - and ahead of subclasses' own hotkeys (each
        # subclass's modal() calls super().modal() first and must bail out
        # via self.numeric_input_active before running its own key checks).
        if self.numeric_input_active:
            return self.handle_numeric_input(context, event)

        if event.value == 'PRESS':
            active_numeric_field = self.get_active_numeric_field()
            if active_numeric_field:
                char = self._numeric_char_for_event(event)
                if char:
                    self.start_numeric_input(active_numeric_field, char)
                    return {'RUNNING_MODAL'}

        # User Input
        # aboard operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_cleanup(context)
            return {'CANCELLED'}

        # apply operator
        elif event.type in {'LEFTMOUSE', 'NUMPAD_ENTER', 'RET'}:
            # Flush any debounced decimate/remesh re-evaluation immediately
            # rather than leaving it to the background timer: the timer
            # would still fire a little later, but the accepted result
            # should reflect the last dragged value right away, not after a
            # brief visible lag.
            if self.decimate_timer_scheduled:
                self.decimate_timer_scheduled = False
                self.apply_decimate_value(context)
            if self.remesh_timer_scheduled:
                self.remesh_timer_scheduled = False
                self.apply_remesh_value(context)

            if bpy.context.space_data.shading.color_type:
                context.space_data.shading.color_type = self.color_type

            if len(self.new_colliders_list) == 0:
                self.report({'WARNING'}, "No Colliders generated")

            # Pass 1: origin recentre, custom rotation, modifier cleanup, display
            # settings.  No depsgraph update needed between iterations because
            # each collider is independent of the others.
            #
            # Fetch the evaluated depsgraph once before the loop.
            # set_origin_to_center_of_mass() calls evaluated_depsgraph_get()
            # internally; after each obj.location = com the depsgraph is
            # dirtied, causing the next per-call get to force a full scene
            # re-evaluation — O(N²) for N colliders.  Passing the same
            # depsgraph to every call keeps each object's evaluated data
            # correct (it was unmodified when the depsgraph was fetched) while
            # eliminating the hidden per-iteration re-evaluation.
            _depsgraph = (
                bpy.context.evaluated_depsgraph_get()
                if self.use_recenter_origin and not self.join_primitives
                else None
            )
            for i, obj in enumerate(self.new_colliders_list):
                if not obj:
                    continue

                if not self.join_primitives:
                    if self.use_recenter_origin:
                        # set origin causes issues. Does not work properly
                        set_origin_to_center_of_mass(obj, _depsgraph)
                        # center = self.calculate_center_of_mass(obj)
                        # if not self.debug_parenting_off:
                        #     self.set_custom_origin_location(obj, center)

                    if self.use_custom_rotation:
                        if len(self.col_rotation_matrix_list) > 0:
                            self.set_custom_rotation(obj, self.col_rotation_matrix_list[i])

                # remove modifiers if they have the default value
                if not self.prefs.keep_modifier_defaults:
                    if self.current_settings_dic['displace_offset'] == 0.0:
                        self.del_displace_modifier(obj)
                    if self.current_settings_dic['decimate'] == 1.0:
                        self.del_decimate_modifier(obj)

                # set the display settings for the collider objects
                obj.display_type = colSettings.display_type
                if self.prefs.hide_render_on_creation:
                    obj.hide_render = True

                if self.prefs.my_hide:
                    obj.hide_viewport = self.prefs.my_hide

                if self.prefs.wireframe_mode == 'ALWAYS':
                    obj.show_wire = True
                else:
                    obj.show_wire = False

            # Pass 2: fix parent inverse matrix.  A single depsgraph update
            # before the loop propagates the location changes from Pass 1 so
            # that fix_inverse_matrix() reads correct matrix_world values.
            # Skipping the per-object update inside fix_inverse_matrix() (via
            # update_depsgraph=False) reduces 2N depsgraph evaluations to 2.
            if self.prefs.fix_parent_inverse_mtrx:
                from ..collider_operators.utility_operators import fix_inverse_matrix, fix_inverse_matrix_is_safe
                bpy.context.view_layer.update()
                skipped_names = []
                for obj in self.new_colliders_list:
                    if not obj or not obj.parent:
                        continue
                    if not fix_inverse_matrix_is_safe(obj):
                        print(f"Skipping {obj.name}: parent-relative transform contains shear that "
                              f"can't be baked without distorting the mesh.")
                        skipped_names.append(obj.name)
                        continue
                    # fix_inverse_matrix() re-expresses the parent-relative transform on
                    # obj.location/rotation_euler/scale rather than baking it into the mesh, so
                    # it's safe to run even when use_custom_rotation set a custom rotation above:
                    # that rotation is preserved, just relative to a now-uncancelled parent.
                    fix_inverse_matrix(obj, update_depsgraph=False)
                bpy.context.view_layer.update()
                if skipped_names:
                    self.report(
                        {'WARNING'},
                        f"Skipped {len(skipped_names)} collider(s) whose parent-relative transform "
                        f"contains shear and can't be reset safely: {', '.join(skipped_names)}.",
                    )

            # Pass 3: optional auto-apply Collider Cleanup operations, each
            # opt-in via its own preference (both default off). Runs after the
            # parent-inverse fix so it sees the final, cleaned-up transforms.
            if self.prefs.auto_apply_origin_to_parent or self.prefs.auto_apply_tris_limit:
                from ..collider_operators.utility_operators import move_origin_to_parent, set_triangle_count_limit

                if self.prefs.auto_apply_origin_to_parent:
                    for obj in self.new_colliders_list:
                        if obj:
                            move_origin_to_parent(obj)
                    bpy.context.view_layer.update()

                if self.prefs.auto_apply_tris_limit:
                    _tris_depsgraph = bpy.context.evaluated_depsgraph_get()
                    unreachable_names = []
                    for obj in self.new_colliders_list:
                        if not obj:
                            continue
                        if not set_triangle_count_limit(obj, self.prefs.auto_apply_max_triangle_count,
                                                         depsgraph=_tris_depsgraph):
                            unreachable_names.append(obj.name)
                    if unreachable_names:
                        self.report(
                            {'WARNING'},
                            f"Auto tris-limit: cannot reach {self.prefs.auto_apply_max_triangle_count} tris "
                            f"even at maximum decimation for: {', '.join(unreachable_names)}.",
                        )

            # Delete temporary generated meshes
            self.remove_objects(self.tmp_meshes)
            self.remove_empty_collection(context, 'tmp_mesh')
            self._clear_modifier_bake_cache()

            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            # restore display settings
            self.reset_display(context)

            return {'FINISHED'}

        # Set ref values when switching mode to avoid jumping of field of view.
        elif event.type in ['LEFT_SHIFT', 'LEFT_CTRL'] and event.value in ['PRESS', 'RELEASE']:
            self.ref_settings_dic = self.current_settings_dic.copy()

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x
            # Alt is not pressed anymore after release
            self.ignore_input = False

            return {'RUNNING_MODAL'}

        # Ignore Mouse Movement. The Operator will behave as starting it newly
        elif event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            self.ref_settings_dic = self.current_settings_dic.copy()

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x
            self.mouse_position = [event.mouse_x, event.mouse_y]

            # Alt is not pressed anymore after release
            self.ignore_input = False
            self.force_redraw()
            return {'RUNNING_MODAL'}

        elif event.type == 'C' and event.value == 'RELEASE':
            self.x_ray = not self.x_ray
            context.space_data.shading.show_xray = self.x_ray
            # Another function needs to be called for the modal UI to update :(
            self.set_collisions_wire_preview(self.prefs.wireframe_mode)

        elif event.type == 'J' and event.value == 'RELEASE':
            self.join_primitives = not self.join_primitives
            if self.join_primitives:
                self.shape = "mesh_shape"
            else:
                self.shape = self.initial_shape
            self.execute(context)

        elif event.type == 'I' and event.value == 'RELEASE':
            self.use_loose_mesh = not self.use_loose_mesh
            self.execute(context)

        elif event.type == 'M' and event.value == 'RELEASE' and self.use_creation_mode:
            if self.obj_mode == 'OBJECT' and not self.is_mesh_to_collider:
                length = len(self.creation_mode)
            else:
                length = len(self.creation_mode_edit)
            self.creation_mode_idx = (self.creation_mode_idx + 1) % length

            self.execute(context)

        elif event.type == 'V' and event.value == 'RELEASE':
            # toggle through display modes
            if context.space_data.shading.type == 'SOLID':
                self.is_solidmode = True
                self.shading_idx = (self.shading_idx + 1) % len(self.shading_modes)
                context.space_data.shading.color_type = self.shading_modes[self.shading_idx]
            else:
                self.is_solidmode = not self.is_solidmode

        elif event.type == 'O' and event.value == 'RELEASE' and self.use_keep_original_materials == True:
            self.keep_original_material = not self.keep_original_material
            # Numbers are indices of the Vierport mode of the color type properties: 0 = Object, 1 = Material, 3 = Single color
            idx = 1 if self.keep_original_material else 0
            context.space_data.shading.color_type = self.shading_modes[idx]

            for objinfo in self.original_obj_data:
                ob = objinfo['obj']
                collections = objinfo['users_collection']
                for col in collections:
                    try:
                        bpy.data.collections[col].objects.link(ob)
                    except:
                        pass

            self.execute(context)

        elif event.type == 'N' and event.value == 'RELEASE' and self.use_keep_original_name:
            self.keep_original_name = not self.keep_original_name
            self.execute(context)

        elif event.type == 'S' and event.value == 'RELEASE':

            self.set_modal_state(displace_active=not self.displace_active)
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'D' and event.value == 'RELEASE':
            self.set_modal_state(decimate_active=not self.decimate_active)

            self.mouse_initial_x = event.mouse_x
            self.mouse_position = [event.mouse_x, event.mouse_y]
            self.draw_callback_px(context)

        elif event.type == 'A' and event.value == 'RELEASE':
            self.set_modal_state(opacity_active=not self.opacity_active)
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'E' and event.value == 'RELEASE':
            self.set_modal_state(cylinder_segments_active=not self.cylinder_segments_active)
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'H' and event.value == 'RELEASE':
            self.set_modal_state(height_active=not self.height_active)
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'W' and event.value == 'RELEASE':
            self.set_modal_state(width_active=not self.width_active)
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'Q' and event.value == 'RELEASE':
            # toggle through display modes
            self.collider_shapes_idx = (self.collider_shapes_idx + 1) % len(self.collider_shapes)
            self.shape = self.collider_shapes[self.collider_shapes_idx]
            for collider in self.new_colliders_list:
                if collider:
                    collider['collider_shape'] = self.shape
            self.update_names()

        elif event.type == 'T' and event.value == 'RELEASE' and self.collider_groups_enabled:
            # toggle through display modes
            self.collision_group_idx = (self.collision_group_idx + 1) % len(self.collision_groups)
            col = self.collision_groups[self.collision_group_idx].color
            for obj in self.new_colliders_list:
                set_object_color(obj, (col[0], col[1], col[2], self.current_settings_dic['alpha']))
                self.set_object_collider_group(obj)
            self.update_names()

        elif event.type == 'MOUSEMOVE':
            # calculate mouse movement and offset camera
            delta = int(self.mouse_initial_x - event.mouse_x)
            self.mouse_position = [event.mouse_x, event.mouse_y]

            # Ignore if Alt is pressed
            if event.alt:
                self.ignore_input = True
                return {'RUNNING_MODAL'}

            if self.displace_active:
                offset = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                strength = self.ref_settings_dic['displace_offset'] - offset

                for mod in self.displace_modifiers:
                    mod.strength = strength
                    mod.show_on_cage = True
                    mod.show_in_editmode = True

                self.current_settings_dic['displace_offset'] = strength

            if self.decimate_active:
                delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                dec_amount = (self.ref_settings_dic['decimate'] + delta)
                dec_amount = numpy.clip(dec_amount, 0.01, 1.0)

                if self.current_settings_dic['decimate'] != dec_amount:
                    self.current_settings_dic['decimate'] = dec_amount
                    # Debounce the actual re-evaluation (see apply_decimate_value):
                    # it forces a depsgraph update per collider, which is too slow
                    # to run on every intermediate mouse-move delta.
                    self.decimate_debounce_until = time.time() + MODIFIER_DEBOUNCE_SECONDS
                    self.arm_decimate_timer()

            if self.remesh_active:
                delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                multiplier = (self.ref_settings_dic['voxel_size_multiplier'] + delta)
                multiplier = numpy.clip(multiplier, 0.001, 1.0)

                if self.current_settings_dic['voxel_size_multiplier'] != multiplier:
                    self.current_settings_dic['voxel_size_multiplier'] = multiplier
                    # Debounce the actual re-evaluation (see apply_remesh_value):
                    # for subclasses that rebuild the mesh from scratch (voxel
                    # grid), re-running on every delta falls behind the input
                    # and the viewport stutters/freezes (#641).
                    self.remesh_debounce_until = time.time() + MODIFIER_DEBOUNCE_SECONDS
                    self.arm_remesh_timer()

            if self.opacity_active and self.shading_modes[self.shading_idx] == 'OBJECT':
                delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                color_alpha = self.ref_settings_dic['alpha'] - delta
                color_alpha = numpy.clip(color_alpha, 0.00, 1.0)

                for obj in self.new_colliders_list:
                    obj.color[3] = color_alpha

                self.prefs.user_groups_alpha = color_alpha
                self.current_settings_dic['alpha'] = color_alpha

            if self.cylinder_segments_active:
                delta = self.get_delta_value(delta, event, sensibility=0.02, tweak_amount=10)
                segment_count = int(abs(self.ref_settings_dic['cylinder_segments'] - delta))

                # check if value changed to avoid regenerating collisions for the same value
                if segment_count != int(round(self.current_settings_dic['cylinder_segments'])):
                    segment_count = 3 if segment_count < 3 else segment_count
                    self.current_settings_dic['cylinder_segments'] = segment_count
                    self.execute(context)

            if self.height_active:
                # delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                offset = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                strength = self.ref_settings_dic['height_mult'] - offset
                height_mult = strength
                height_mult = numpy.clip(height_mult, 0, 10.0)

                if self.current_settings_dic['height_mult'] != height_mult:
                    self.current_settings_dic['height_mult'] = height_mult
                    self.execute(context)

            if self.width_active:
                offset = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precision=1)
                strength = self.ref_settings_dic['width_mult'] - offset
                width_mult = strength
                width_mult = numpy.clip(width_mult, 0, 10.0)

                if self.current_settings_dic['width_mult'] != width_mult:
                    self.current_settings_dic['width_mult'] = width_mult
                    self.execute(context)

            if self.sphere_segments_active:
                delta = self.get_delta_value(delta, event, sensibility=0.02, tweak_amount=10)
                segments = int(abs(self.ref_settings_dic['sphere_segments'] - delta))

                # check if value changed to avoid regenerating collisions for the same value
                if segments != int(round(self.current_settings_dic['sphere_segments'])):
                    segments = 2 if segments < 2 else segments
                    self.current_settings_dic['sphere_segments'] = segments
                    self.execute(context)

            if self.capsule_segments_active:
                delta = self.get_delta_value(delta, event, sensibility=0.02, tweak_amount=10)
                segments = int(abs(self.ref_settings_dic['capsule_segments'] - delta))

                # check if value changed to avoid regenerating collisions for the same value
                if segments != int(round(self.current_settings_dic['capsule_segments'])):
                    self.current_settings_dic['capsule_segments'] = segments
                    self.execute(context)

        # passthrough specific events to blenders default behavior
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # get current time to calculate time elapsed
        self.t0 = time.time()
        # reset naming count:
        self.name_count = 0
        self._naming_cache = {}

        # Bug:
        try:
            self.obj_mode = context.object.mode
        except AttributeError:
            print("AttributeError: bug #328")

        colSettings = context.scene.simple_collider

        if not colSettings.get('visibility_toggle_user_group_01'):
            set_default_group_values()

        # Remove objects from previous generation
        self.remove_objects(self.tmp_meshes)

        self.remove_objects(self.new_colliders_list)
        self.remove_empty_collection(context, 'tmp_mesh')
        self.new_colliders_list = []
        self.original_obj_data = []
        self.tmp_meshes = []

        # original data to be restored on cancellation or deleted on accept
        self.original_obj_data = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []
        self.remesh_modifiers = []
        self.remesh_data = []

        # Create the bounding geometry, depending on edit or object mode.
        self.old_objs = set(context.scene.objects)
