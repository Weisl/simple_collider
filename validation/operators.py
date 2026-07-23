import bpy

from .. import __package__ as base_package
from .checks import collect_validation_issues


_SHAPE_ICON = {
    'box_shape': 'MESH_CUBE',
    'sphere_shape': 'MESH_UVSPHERE',
    'capsule_shape': 'MESH_CAPSULE',
    'convex_shape': 'MESH_ICOSPHERE',
    'mesh_shape': 'MESH_MONKEY',
    'voxel_shape': 'MESH_GRID',
}


def _object_icon(object_name):
    """Icon representing the object's collider shape, or a generic object
    icon for a render mesh (e.g. the object named by a missing_collider
    issue, which isn't itself a collider)."""
    obj = bpy.data.objects.get(object_name)
    if obj is not None:
        icon = _SHAPE_ICON.get(obj.get('collider_shape'))
        if icon:
            return icon
    return 'OBJECT_DATA'


class COLLISION_UL_validation_results(bpy.types.UIList):
    """List of collider validation issues, grouped by the object they concern
    (a bold header naming the object precedes its issues, since the flat
    results collection is already grouped in that order - collect_validation_
    issues() appends every issue for one object before moving to the next).
    Each row has a dedicated arrow button to select/frame the object (see
    COLLISION_OT_select_validation_object); the message itself is a plain,
    non-interactive label."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        results = data.simple_collider_validation_results
        is_group_start = index == 0 or results[index - 1].object_name != item.object_name

        col = layout.column(align=True)
        if is_group_start:
            col.label(text=item.object_name, icon=_object_icon(item.object_name))

        row = col.row(align=True)
        select_op = row.operator('collision.select_validation_object', text='', icon='FORWARD')
        select_op.object_name = item.object_name
        severity_icon = 'ERROR' if item.severity == 'ERROR' else 'INFO'
        row.label(text=item.message, icon=severity_icon)


def _frame_selected(context):
    """Best-effort viewport framing after a selection change from within the
    validation popup. Selection itself is the important part of the action -
    framing is skipped rather than raised as an error if no 3D viewport can
    be found (e.g. a very unusual screen layout)."""
    if context.area and context.area.type == 'VIEW_3D' and context.region:
        with context.temp_override(area=context.area, region=context.region):
            bpy.ops.view3d.view_selected()
        return

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            with context.temp_override(window=window, area=area, region=region):
                bpy.ops.view3d.view_selected()
            return


class COLLISION_OT_select_validation_object(bpy.types.Operator):
    """Select and frame the object referenced by this validation result"""
    bl_idname = "collision.select_validation_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'INTERNAL'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj is None:
            self.report({'WARNING'}, f"Object '{self.object_name}' no longer exists")
            return {'CANCELLED'}

        for selected in context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        _frame_selected(context)

        return {'FINISHED'}


class COLLISION_OT_copy_validation_report(bpy.types.Operator):
    """Copy the validation report to the clipboard"""
    bl_idname = "collision.copy_validation_report"
    bl_label = "Copy Report to Clipboard"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        wm = context.window_manager
        results = wm.simple_collider_validation_results
        if not results:
            self.report({'INFO'}, "No validation issues to copy")
            return {'CANCELLED'}

        lines = []
        current_object = None
        for item in results:
            if item.object_name != current_object:
                if current_object is not None:
                    lines.append('')
                lines.append(item.object_name)
                current_object = item.object_name
            lines.append(f"  [{item.severity}] {item.message}")

        wm.clipboard = '\n'.join(lines)
        self.report({'INFO'}, "Validation report copied to clipboard")
        return {'FINISHED'}


class COLLISION_OT_validate_colliders(bpy.types.Operator):
    """Check colliders in the scene for common problems"""
    bl_idname = "collision.validate_colliders"
    bl_label = "Validate Colliders"
    bl_options = {'REGISTER'}

    scope: bpy.props.EnumProperty(
        name="Scope",
        items=(
            ('VIEW_LAYER', "Whole Scene", "Check every object in the current view layer"),
            ('SELECTION', "Selected Objects", "Check only the currently selected objects"),
        ),
        default='VIEW_LAYER',
        update=lambda self, context: self._rescan(context),
    )

    def _objects(self, context):
        if self.scope == 'SELECTION':
            return context.selected_objects
        return context.view_layer.objects

    def _rescan(self, context):
        prefs = context.preferences.addons[base_package].preferences
        depsgraph = context.evaluated_depsgraph_get()
        issues = collect_validation_issues(self._objects(context), prefs, depsgraph)

        wm = context.window_manager
        results = wm.simple_collider_validation_results
        results.clear()
        for issue in issues:
            item = results.add()
            item.check_id = issue.check_id
            item.object_name = issue.object_name
            item.severity = issue.severity
            item.message = issue.message
        wm.simple_collider_validation_index = 0

    def invoke(self, context, event):
        self._rescan(context)

        if len(context.window_manager.simple_collider_validation_results) == 0:
            self.report({'INFO'}, "No collider issues found")
            return {'FINISHED'}

        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        row = layout.row()
        row.prop(self, 'scope', expand=True)

        count = len(wm.simple_collider_validation_results)
        layout.label(text=f"{count} issue(s) found", icon='ERROR' if count else 'CHECKMARK')

        layout.template_list(
            'COLLISION_UL_validation_results', '',
            wm, 'simple_collider_validation_results',
            wm, 'simple_collider_validation_index',
            rows=8,
        )

        layout.operator('collision.copy_validation_report', icon='COPYDOWN')

    def execute(self, context):
        return {'FINISHED'}
