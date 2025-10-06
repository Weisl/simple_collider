import bpy
import os
import platform
import textwrap
from bpy.types import Menu
from bpy_extras.io_utils import ImportHelper

from .. import __package__ as base_package


# needed for adding direct link to settings
def get_addon_name():
    """
    Get the name of the addon.

    Returns:
        str: The name of the addon.
    """
    return "Simple Collider"


def collider_presets_folder():
    """
    Ensure the existence of the presets folder for the addon and return its path.

    Returns:
        str: The path to the collider presets directory.
    """
    # Make sure there is a directory for presets
    collider_presets = "simple_collider"
    collider_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", collider_presets)
    collider_preset_paths = bpy.utils.preset_paths(collider_presets)

    if (collider_preset_directory not in collider_preset_paths) and (not os.path.exists(collider_preset_directory)):
        os.makedirs(collider_preset_directory)

    return collider_preset_directory


def draw_auto_convex(layout, context):
    """
    Draw the auto convex options in the layout based on the current platform and preferences.

    Args:
        layout (Layout): The layout to draw the options on.
        context (Context): The current context.
    """

    prefs = context.preferences.addons[base_package].preferences
    addon_name = get_addon_name()

    # row.label(text='Auto Convex')

    if platform.system() not in ['Windows', 'Linux']:
        op = layout.operator("simple_collider.open_preferences", text="", icon='PREFERENCES')
        op.addon_name = addon_name
        op.prefs_tabs = 'VHACD'

        text = "Auto convex is only supported for Windows and Linux at this moment."
        label_multiline(
            context=context,
            text=text,
            parent=layout
        )
    else:
        # col = draw_auto_convex_settings(colSettings, layout)

        if prefs.executable_path or prefs.default_executable_path:

            layout.operator("button.auto_convex", text="Auto Convex", icon='WINDOW')
            op = layout.operator("simple_collider.open_preferences", text="", icon='PREFERENCES')
            op.addon_name = addon_name
            op.prefs_tabs = 'VHACD'
        else:
            op = layout.operator("simple_collider.open_preferences", text="Setup V-HACD", icon='ERROR')
            op.addon_name = addon_name
            op.prefs_tabs = 'VHACD'


def draw_auto_convex_settings(colSettings, layout):
    """
    Draw the settings for auto convex in the layout.

    Args:
        colSettings (UILayout): The column layout to draw the settings on.
        layout (Layout): The parent layout.
    """
    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(colSettings, 'vhacd_shrinkwrap')
    row = col.row(align=True)
    row.prop(colSettings, 'maxHullAmount')
    row.prop(colSettings, 'maxHullVertCount')
    row = col.row(align=True)
    row.prop(colSettings, 'voxelResolution')


def label_multiline(context, text, parent):
    """
    Draw a label with multiline text in the layout.

    Args:
        context (Context): The current context.
        text (str): The text to display.
        parent (UILayout): The parent layout to add the label to.
    """
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


def draw_group_properties(context, property, col_01, col_02, mode, user_group=False):
    """
    Draw the group properties in the layout.

    Args:
        context (Context): The current context.
        property (Property): The property to display.
        col_01 (UILayout): The first column layout.
        col_02 (UILayout): The second column layout.
        mode (str): The mode of the group.
        user_group (bool, optional): Whether the group is a user group. Defaults to False.
    """
    from ..groups.user_groups import get_groups_color, get_groups_name

    group_identifier = mode
    group_name = get_groups_name(mode)
    color = get_groups_color(mode)

    if user_group:
        split = col_01.split(factor=0.95, align=True)
        col_a = split.column(align=True)
        col_b = split.column(align=True)

        row = col_a.row(align=True)
        op = row.operator('object.assign_user_group', text='', icon='FORWARD')
        op.mode = group_identifier
        row.label(text=group_name)

        row = col_b.row(align=True)
        row.enabled = False
        row.prop(property, "color", text='')

    else:
        row = col_01.row(align=True)
        row.label(text=group_name)

    row = col_02.row(align=True)

    if property.hide:
        row.prop(property, 'hide', text=str(property.hide_text), icon=str(property.hide_icon))
    else:
        row.prop(property, 'hide', text=str(property.show_text), icon=str(property.show_icon))

    op = row.operator("object.all_select_collisions", icon=str(property.selected_icon),
                      text=str(property.selected_text))
    op.select = True
    op.mode = group_identifier

    op = row.operator("object.all_delete_collisions", icon=str(property.delete_icon), text=str(property.delete_text))
    op.mode = group_identifier


def draw_visibility_selection_menu(context, layout):
    """
    Draw the visibility selection menu in the layout.

    Args:
        context (Context): The current context.
        layout (UILayout): The layout to draw the menu on.
    """
    split_factor = 0.7

    split_left = layout.split(factor=split_factor, align=True)
    col_01 = split_left.column(align=True)
    col_02 = split_left.column(align=True)

    colSettings = context.scene.simple_collider

    draw_group_properties(context, colSettings.visibility_toggle_all, col_01, col_02, 'ALL_COLLIDER')
    draw_group_properties(context, colSettings.visibility_toggle_obj, col_01, col_02, 'OBJECTS')

    prefs = context.preferences.addons[base_package].preferences

    if prefs.collider_groups_enabled:
        split_left = layout.split(factor=split_factor, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        draw_group_properties(context, colSettings.visibility_toggle_user_group_01, col_01, col_02, 'USER_01',
                              user_group=True)
        draw_group_properties(context, colSettings.visibility_toggle_user_group_02, col_01, col_02, 'USER_02',
                              user_group=True)
        draw_group_properties(context, colSettings.visibility_toggle_user_group_03, col_01, col_02, 'USER_03',
                              user_group=True)


def draw_creation_menu(context, layout, settings=False):
    """
    Draw the creation menu in the layout.

    Args:
        context (Context): The current context.
        layout (UILayout): The layout to draw the menu on.
        settings (bool, optional): Whether to include settings. Defaults to False.
    """
    colSettings = context.scene.simple_collider

    # layout.separator()
    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator("mesh.add_bounding_capsule", icon='MESH_CAPSULE')
    row = col.row(align=True)
    row.operator("mesh.add_remesh_collision", icon='MOD_REMESH')
    row = col.row(align=True)
    row.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')

    # layout.separator()
    row = col.row(align=True)
    draw_auto_convex(row, context)

    row = layout.row(align=True)
    row.label(text='Convert Shape')

    # row = layout.row(align=True)
    # row.scale_x = 1.0  # Ensure buttons take up the full width

    shapes = [{'identifier': 'box_shape', 'text': '', 'icon': 'MESH_CUBE'},
              {'identifier': 'sphere_shape', 'text': '', 'icon': 'MESH_UVSPHERE'},
              {'identifier': 'capsule_shape', 'text': '', 'icon': 'MESH_CAPSULE'},
              {'identifier': 'convex_shape', 'text': '', 'icon': 'MESH_ICOSPHERE'},
              {'identifier': 'mesh_shape', 'text': '', 'icon': 'MESH_MONKEY'},
              ]

    button_amount = len(shapes)

    # Use layout.split() to divide the row into equal parts
    split = layout.split(factor=1.0 / button_amount, align=True)

    for shape in shapes:
        # Create a column for each button
        col = split.column(align=True)
        op = col.operator('object.assign_collider_shape', text=shape['text'], icon=shape['icon'])
        op.shape_identifier = shape['identifier']

    row = layout.row(align=True)
    row.label(text='Convert')

    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator('object.convert_to_collider', icon='PHYSICS')
    row = col.row(align=True)
    row.operator('object.convert_to_mesh', icon='WINDOW')

    row = layout.row(align=True)
    row.operator('object.convert_from_name', icon='NONE')

    row = layout.row(align=True)
    row.operator('object.regenerate_name', icon='FILE_REFRESH')

    layout.separator()

    row = layout.row(align=True)
    row.label(text='Rigid Body')

    row = layout.row(align=True)
    row.operator('object.set_rigid_body', icon='NONE')

    row = layout.row(align=True)
    row.label(text='Operators')
    box = layout.box()
    box.menu("OBJECT_MT_adjust_decimation_menu", text="Cleanup Collider", icon='COLLAPSEMENU')

    row = layout.row(align=True)
    row.label(text='Display as')
    row.prop(colSettings, 'display_type', text='')
    row.prop(colSettings, 'toggle_wireframe', text='', icon='SHADING_WIRE')


def draw_naming_presets(self, context):
    """
    Draw the naming presets menu in the layout.

    Args:
        self (UILayout): The UI layout.
        context (Context): The current context.
    """
    layout = self.layout
    row = layout.row(align=True)

    row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)

    addon_name = get_addon_name()

    op = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
    op.operation = 'FOLDER_OPEN'
    op.filepath = collider_presets_folder()

    op = row.operator("simple_collider.open_preferences", text="", icon='PREFERENCES')
    op.addon_name = addon_name
    op.prefs_tabs = 'NAMING'


# OPERATORS 

class EXPLORER_OT_open_directory_new(bpy.types.Operator, ImportHelper):
    """Open render output directory in Explorer"""
    bl_idname = "explorer.open_in_explorer"
    bl_label = "Open Folder"
    bl_description = "Open preset folder in explorer"

    dirpath: bpy.props.StringProperty(default='/')
    filename_ext = ".py"
    filter_glob: bpy.props.StringProperty(
        default='*.py',
        options={'HIDDEN'}
    )

    def check(self, context):
        # Ensure that the selected file is actually a Python file
        return self.filepath.lower().endswith('.py')

    def invoke(self, context, event):
        # Clear the default file name in the file selection dialog
        if os.path.isdir(self.dirpath):
            if not self.dirpath.lower().endswith('/'):
                self.dirpath += '/'
            self.filepath = self.dirpath
            return super().invoke(context, event)
        else:
            self.report({'ERROR'}, 'Invalid Preset Path')

    def execute(self, context):
        if not self.check(context):
            self.report({'ERROR'}, "Selected file is not a Python file.")
            return {'CANCELLED'}
        self.dirpath = self.filepath
        return {'FINISHED'}


class PREFERENCES_OT_open_addon(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "simple_collider.open_preferences"
    bl_label = "Open Addon preferences"

    addon_name: bpy.props.StringProperty()
    prefs_tabs: bpy.props.StringProperty()

    def execute(self, context):

        bpy.ops.screen.userpref_show()

        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = self.addon_name

        prefs = context.preferences.addons[base_package].preferences
        prefs.prefs_tabs = self.prefs_tabs

        import addon_utils
        mod = addon_utils.addons_fake_modules.get('simple_collider')

        # mod is None the first time the operation is called :/
        if mod:
            mod.bl_info['show_expanded'] = True

            # Find User Preferences area and redraw it
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'USER_PREFERENCES':
                        area.tag_redraw()

        bpy.ops.preferences.addon_expand(module=self.addon_name)
        return {'FINISHED'}


############## PRESET ##############################

class OBJECT_MT_collision_presets(Menu):
    """Collider preset dropdown"""

    bl_label = "Collider Presets"
    bl_description = "Specify creation preset used for the collider generation"
    preset_subdir = "simple_collider"
    preset_operator = "collision.load_collision_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


############## PANELS ##############################

class VIEW3D_PT_collision(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Collider"


# abstract class
class VIEW3D_PT_init():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bpy.context.scene.simple_collider.visibility_toggle_all.mode = 'ALL_COLLIDER'
        bpy.context.scene.simple_collider.visibility_toggle_obj.mode = 'OBJECTS'


class VIEW3D_PT_collision_panel(VIEW3D_PT_collision):
    """Creates a Panel in the Object properties window"""
    bl_label = "Simple Collider"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("wm.url_open", text="", icon='HELP').url = "https://weisl.github.io/collider-tools_overview/"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        draw_naming_presets(self, context)

        # Create Collider
        row = layout.row(align=True)
        row.label(text='Add Collider Shape')

        col = self.layout.column(align=True)
        row = col.row(align=True)
        row.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        row = col.row(align=True)
        row.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')
        row = col.row(align=True)
        row.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')
        row = col.row(align=True)
        row.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
        row = col.row(align=True)
        row.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        draw_creation_menu(context, layout, settings=True)


class VIEW3D_PT_collision_visibility_panel(VIEW3D_PT_collision, VIEW3D_PT_init):
    """Creates a Panel in the Object properties window"""

    # bl_label = "Collider Groups"
    bl_label = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator('view.collider_view_object', icon='HIDE_OFF', text='Collider Groups')
        row.operator("wm.url_open", text="", icon='HELP').url = "https://weisl.github.io/collider-tools_groups/"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        draw_visibility_selection_menu(context, layout)
        layout.separator()


class VIEW3D_PT_collision_settings_panel(VIEW3D_PT_collision):
    """Creates a Panel in the Object properties window"""

    bl_label = "Tool Defaults"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='TOOL_SETTINGS')

    def draw(self, context):
        layout = self.layout
        colSettings = context.scene.simple_collider

        # Bools
        row = layout.row(align=True)
        row.prop(colSettings, "default_modifier_stack")
        row = layout.row(align=True)
        row.prop(colSettings, "default_use_loose_island")
        row = layout.row(align=True)
        row.prop(colSettings, "default_join_primitives")
        row = layout.row(align=True)

        # Dropdowns

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(colSettings, "default_keep_original_material")
        row = col.row(align=True)
        row.prop(colSettings, "default_color_type")
        col.separator
        row = col.row(align=True)
        row.prop(colSettings, "default_space")
        row = col.row(align=True)
        row.prop(colSettings, "default_creation_mode")
        row = col.row(align=True)
        col.separator
        row.prop(colSettings, "default_user_group")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(colSettings, "default_cylinder_axis")
        row = col.row(align=True)
        row.prop(colSettings, "default_cylinder_segments")
        row = col.row(align=True)
        row.prop(colSettings, "default_sphere_segments")


class VIEW3D_PT_collision_material_panel(VIEW3D_PT_collision):
    """Creates a Panel in the Object properties window"""

    # bl_label = "Physics Materials"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator('view.collider_view_material', icon='HIDE_OFF', text='Physics Materials')
        row.operator("wm.url_open", text="",
                     icon='HELP').url = "https://weisl.github.io/collider-tools_physics_materials/"

    def draw(self, context):
        layout = self.layout
        colSettings = context.scene.simple_collider
        prefs = context.preferences.addons[base_package].preferences

        layout.label(text='Active Material')
        # self.draw_active_physics_material(colSettings, layout)
        scene = context.scene
        activeMat = scene.active_physics_material

        split_left = layout.split(factor=0.75, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        col_01.prop_search(scene, "active_physics_material", bpy.data, "materials", text='')
        if activeMat:
            col_02.prop(activeMat, 'diffuse_color', text='')

        if prefs.use_physics_material:
            layout.label(text='Material List')
            layout.template_list("MATERIAL_UL_physics_materials", "", bpy.data, "materials", colSettings,
                                 "material_list_index")

            box = layout.box()
            col = box.column(align=True)
            col.operator('material.create_physics_material', icon='ADD', text="Add Physics Material")

    def draw_active_physics_material(self, colSettings, layout):
        split_left = layout.split(factor=0.75, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)
        mat = bpy.data.materials[colSettings.material_list_index]
        col_01.prop(mat, "name", text="")
        col_02.prop(mat, "diffuse_color", text='')


############## MENUS ##############################

class VIEW3D_MT_collision_creation(Menu):
    bl_label = 'Collision Creation'

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Generation')

        draw_creation_menu(context, layout)


############## PIE ##############################

class COLLISION_MT_pie_menu(Menu, VIEW3D_PT_init):
    # label is displayed at the center of the pie menu.
    bl_label = "Collider Pie"
    bl_idname = "COLLISION_MT_pie_menu"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        # West
        pie.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        # East
        pie.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')

        # South
        split = pie.split()
        split.scale_x = 1.5

        b = split.box()
        column = b.column()
        column.menu_contents("VIEW3D_MT_collision_creation")

        split_factor = 0.7

        split_left = column.split(factor=split_factor, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        colSettings = context.scene.simple_collider

        draw_group_properties(context, colSettings.visibility_toggle_all, col_01, col_02, 'ALL_COLLIDER')
        draw_group_properties(context, colSettings.visibility_toggle_obj, col_01, col_02, 'OBJECTS')

        # North
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')

        # NorthWest
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        # NorthEast
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')


class BUTTON_OT_auto_convex(bpy.types.Operator):
    """Print object name in Console"""
    bl_idname = "button.auto_convex"
    bl_label = "Auto Convex"

    @classmethod
    def poll(cls, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']:
                count = count + 1
        return count > 0

    def execute(self, context):
        bpy.ops.wm.call_panel(name="POPUP_PT_auto_convex")
        return {'FINISHED'}


class OBJECT_MT_adjust_decimation_menu(Menu):
    bl_label = "Collider Cleanup"
    bl_idname = "OBJECT_MT_adjust_decimation_menu"
    bl_description = "Clean up collider geometry (remove doubles, optimize, etc.)"

    def draw(self, context):
        layout = self.layout
        layout.operator('object.adjust_decimation')
        layout.operator('object.origin_to_parent')
        layout.operator('object.fix_parent_inverse_transform')
        # Use a warning icon for Blender 4.3 and above, else use error icon
        icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'
        layout.operator('collision.replace_with_clean_mesh', icon=icon)
