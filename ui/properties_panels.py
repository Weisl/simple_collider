import bpy
import os
import platform
import subprocess
import textwrap
from bpy.types import Menu

from ..pyshics_materials.material_functions import create_default_material, set_active_physics_material

def collider_presets_folder():
    # Make sure there is a directory for presets
    collider_presets = "collider_tools"
    collider_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", collider_presets)
    collider_preset_paths = bpy.utils.preset_paths(collider_presets)

    if (collider_preset_directory not in collider_preset_paths) and (not os.path.exists(collider_preset_directory)):
        os.makedirs(collider_preset_directory)

    return collider_preset_directory


def get_addon_name():
    # Get Addon Name
    from .. import bl_info
    return bl_info["name"]


def draw_auto_convex(layout, context):
    prefs = context.preferences.addons[__package__.split('.')[0]].preferences
    # colSettings = context.scene.collider_tools
    addon_name = get_addon_name()


    # row.label(text='Auto Convex')

    if platform.system() != 'Windows':
        op = layout.operator("preferences.addon_search", text="", icon='PREFERENCES')
        op.addon_name = addon_name
        op.prefs_tabs = 'VHACD'

        text = "Auto convex is only supported for Windows at this moment."
        label_multiline(
            context=context,
            text=text,
            parent=layout
        )
    else:
        # col = draw_auto_convex_settings(colSettings, layout)

        if prefs.executable_path or prefs.default_executable_path:

            layout.operator("button.auto_convex", text="Auto Convex", icon='WINDOW')
            op = layout.operator("preferences.addon_search", text="", icon='PREFERENCES')
            op.addon_name = addon_name
            op.prefs_tabs = 'VHACD'
        else:
            op = layout.operator("preferences.addon_search", text="Setup V-HACD", icon='ERROR')
            op.addon_name = addon_name
            op.prefs_tabs = 'VHACD'


def draw_auto_convex_settings(colSettings, layout):
    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(colSettings, 'vhacd_shrinkwrap')
    row = col.row(align=True)
    row.prop(colSettings, 'maxHullAmount')
    row.prop(colSettings, 'maxHullVertCount')
    row = col.row(align=True)
    row.prop(colSettings, 'voxelResolution')


def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


def draw_group_properties(context, property, col_01, col_02, user_group=False):
    group_identifier = property.mode
    group_name = property.name

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

    # colSettings = context.scene.collider_tools
    #
    # Test disabling deleting all objects
    # if group_identifier == 'OBJECTS':
    #     row.enabled = False
    # else:
    #     row.enabled = True

    op = row.operator("object.all_delete_collisions", icon=str(property.delete_icon), text=str(property.delete_text))
    op.mode = group_identifier


def draw_visibility_selection_menu(context, layout):
    split_factor = 0.7

    split_left = layout.split(factor=split_factor, align=True)
    col_01 = split_left.column(align=True)
    col_02 = split_left.column(align=True)

    colSettings = context.scene.collider_tools

    draw_group_properties(context, colSettings.visibility_toggle_all, col_01, col_02)
    draw_group_properties(context, colSettings.visibility_toggle_obj, col_01, col_02)

    prefs = context.preferences.addons[__package__.split('.')[0]].preferences

    if prefs.collider_groups_enabled:
        split_left = layout.split(factor=split_factor, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        draw_group_properties(context, colSettings.visibility_toggle_user_group_01, col_01, col_02, user_group=True)
        draw_group_properties(context, colSettings.visibility_toggle_user_group_02, col_01, col_02, user_group=True)
        draw_group_properties(context, colSettings.visibility_toggle_user_group_03, col_01, col_02, user_group=True)


def draw_creation_menu(context, layout, settings=False):
    colSettings = context.scene.collider_tools

    # layout.separator()
    col =layout.column(align=True)
    row = col.row(align=True)
    row.operator("mesh.add_bounding_capsule", icon='MESH_CAPSULE')
    row = col.row(align=True)
    row.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')


    # layout.separator()
    row = col.row(align=True)
    draw_auto_convex(row, context)

    row = layout.row(align=True)
    row.label(text='Convert')

    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator('object.convert_to_collider', icon='PHYSICS')
    row = col.row(align=True)
    row.operator('object.convert_to_mesh', icon='WINDOW')

    row = layout.row(align=True)
    row.operator('object.regenerate_name', icon='FILE_REFRESH')

    layout.separator()

    # row = layout.row(align=True)
    # row.label(text='Display')
    #
    # row = layout.row(align=True)
    # row.operator('view.collider_view_object', icon='HIDE_OFF', text='Groups')
    # row.operator('view.collider_view_material', icon='HIDE_OFF', text='Materials')


    row = layout.row(align=True)
    row.label(text='Display as')
    row.prop(colSettings, 'display_type', text='')
    row.prop(colSettings, 'toggle_wireframe', text='', icon='SHADING_WIRE')


def draw_naming_presets(self, context):
    layout = self.layout
    row = layout.row(align=True)

    row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)

    addon_name = get_addon_name()

    if platform.system() == 'Windows':
        op = row.operator("explorer.open_in_explorer", text="", icon='FILE_FOLDER')
        op.dirpath = collider_presets_folder()

    op = row.operator("preferences.addon_search", text="", icon='PREFERENCES')
    op.addon_name = addon_name
    op.prefs_tabs = 'NAMING'


############## OPERATORS ##############################

class EXPLORER_OT_open_directory_new(bpy.types.Operator):
    """Open render output directory in Explorer"""
    bl_idname = "explorer.open_in_explorer"
    bl_label = "Open Folder"
    bl_description = "Open preset folder in explorer"

    dirpath: bpy.props.StringProperty()

    def execute(self, context):

        if os.path.isdir(self.dirpath):
            subprocess.Popen(["explorer.exe", self.dirpath])
        else:
            self.report({'ERROR'}, 'Invalid Preset Path')
            return {'CANCELLED'}

        return {'FINISHED'}


class PREFERENCES_OT_open_addon(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "preferences.addon_search"
    bl_label = "Open Addon preferences"

    addon_name: bpy.props.StringProperty()
    prefs_tabs: bpy.props.StringProperty()

    def execute(self, context):

        bpy.ops.screen.userpref_show()

        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = self.addon_name

        prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        prefs.prefs_tabs = self.prefs_tabs

        import addon_utils
        mod = addon_utils.addons_fake_modules.get('collider_tools')

        # mod is None the first time the operation is called :/
        if mod:
            mod.bl_info['show_expanded'] = True

            # Find User Preferences area and redraw it
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'USER_PREFERENCES':
                        area.tag_redraw()

        # bpy.ops.preferences.addon_expand(module=self.addon_name)
        return {'FINISHED'}


############## PRESET ##############################

class OBJECT_MT_collision_presets(Menu):
    '''Collider preset dropdown'''

    bl_label = "Presets"
    bl_description = "Specify creation preset used for the collider generation"
    preset_subdir = "collider_tools"
    preset_operator = "script.execute_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


############## PANELS ##############################

class VIEW3D_PT_collision(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collider Tools"

# abstract class
class VIEW3D_PT_init():
    def __init__(self):
        bpy.context.scene.collider_tools.visibility_toggle_all.mode = 'ALL_COLLIDER'
        bpy.context.scene.collider_tools.visibility_toggle_obj.mode = 'OBJECTS'

        bpy.context.scene.collider_tools.visibility_toggle_user_group_01.mode = 'USER_01'
        bpy.context.scene.collider_tools.visibility_toggle_user_group_02.mode = 'USER_02'
        bpy.context.scene.collider_tools.visibility_toggle_user_group_03.mode = 'USER_03'

class VIEW3D_PT_collision_panel(VIEW3D_PT_collision):
    """Creates a Panel in the Object properties window"""
    bl_label = "Collider Tools"

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

    def __init__(self):
        super(VIEW3D_PT_init).__init__()

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
        colSettings = context.scene.collider_tools

        #Bools
        row = layout.row(align=True)
        row.prop(colSettings, "default_modifier_stack")
        row = layout.row(align=True)

        #Dropdowns

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
        colSettings = context.scene.collider_tools
        prefs = context.preferences.addons[__package__.split('.')[0]].preferences

        layout.label(text='Active Material')
        # self.draw_active_physics_material(colSettings, layout)
        scene = context.scene
        activeMat = scene.active_physics_material

        split_left = layout.split(factor=0.75, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        col_01.prop_search(scene, "active_physics_material", bpy.data, "materials", text='')
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

class VIEW3D_MT_PIE_template(Menu, VIEW3D_PT_init):
    # label is displayed at the center of the pie menu.
    bl_label = "Collision Pie"
    bl_idname = "COLLISION_MT_pie_menu"

    def __init__(self):
        super().__init__()

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

        colSettings = context.scene.collider_tools

        draw_group_properties(context, colSettings.visibility_toggle_all, col_01, col_02)
        draw_group_properties(context, colSettings.visibility_toggle_obj, col_01, col_02)


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
            if obj.type == 'MESH':
                count = count + 1
        return count > 0

    def execute(self, context):
        bpy.ops.wm.call_panel(name="POPUP_PT_auto_convex")
        return {'FINISHED'}