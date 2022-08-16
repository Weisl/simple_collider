import bpy
import os
import platform
import subprocess
import textwrap
from bpy.types import Menu


def collider_presets_folder():
    # Make sure there is a directory for presets
    collider_presets = "collider_tools"
    collider_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", collider_presets)
    collider_preset_paths = bpy.utils.preset_paths(collider_presets)

    if (collider_preset_directory not in collider_preset_paths):
        if (not os.path.exists(collider_preset_directory)):
            os.makedirs(collider_preset_directory)

    return collider_preset_directory


def get_addon_name():
    # Get Addon Name
    from .. import bl_info
    return bl_info["name"]


def draw_auto_convex(self, context):
    prefs = context.preferences.addons[__package__.split('.')[0]].preferences
    scene = context.scene
    addon_name = get_addon_name()

    # Auto Convex
    layout = self.layout

    row = layout.row(align=True)
    row.label(text='Auto Convex')

    if platform.system() is not 'Windows':
        text = "Auto convex is only supported for Windows at this moment."
        label_multiline(
            context=context,
            text=text,
            parent=layout
        )
    else:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scene, 'convex_decomp_depth')
        row.prop(scene, 'maxNumVerticesPerCH')
        op = row.operator("preferences.addon_search", text="", icon='PREFERENCES')
        op.addon_name = addon_name
        op.prefs_tabs = 'VHACD'

        row = col.row(align=True)

        if prefs.executable_path:
            row.operator("collision.vhacd", text="Auto Convex", icon='MESH_ICOSPHERE')
        else:
            op = row.operator("preferences.addon_search", text="Install V-HACD", icon='ERROR')
            op.addon_name = addon_name
            op.prefs_tabs = 'VHACD'


def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


def draw_group_properties(context, property, identifier, col_01, col_02):
    select_icon = 'NONE'
    deselect_icon = 'NONE'
    select_text = 'Select'
    deselect_text = 'Deselect'

    delete_icon = 'TRASH'
    delete_text = ''

    group_identifier = identifier
    # group_name = property.name

    row = col_01.row(align=True)
    row.label(text=group_identifier)

    row = col_02.row(align=True)

    if property.hidden:
        row.prop(property, 'hidden', text='', icon='HIDE_OFF')
    else:
        row.prop(property, 'hidden', text='', icon='HIDE_ON')

    op = row.operator("object.all_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = group_identifier
    op = row.operator("object.all_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = group_identifier
    op = row.operator("object.all_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = group_identifier


def draw_visibility_selection_menu(context, layout):
    split_left = layout.split(factor=0.35)
    col_01 = split_left.column(align=True)
    col_02 = split_left.column(align=True)

    scene = context.scene

    draw_group_properties(context, scene.visibility_toggle_all, 'ALL_COLLIDER', col_01, col_02)
    draw_group_properties(context, scene.visibility_toggle_obj, 'OBJECTS', col_01, col_02)

    prefs = context.preferences.addons[__package__.split('.')[0]].preferences
    if prefs.useCustomColGroups:
        box = layout.box()
        split_left = box.split(factor=0.35)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        draw_group_properties(context, scene.visibility_toggle_complex_simple, 'SIMPLE_COMPLEX', col_01, col_02)
        draw_group_properties(context, scene.visibility_toggle_complex, 'SIMPLE', col_01, col_02)
        draw_group_properties(context, scene.visibility_toggle_simple, 'COMPLEX', col_01, col_02)


def draw_naming_presets(self, context):
    layout = self.layout
    row = layout.row(align=True)

    row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)

    addon_name = get_addon_name()

    op = row.operator("preferences.addon_search", text="", icon='PREFERENCES')
    op.addon_name = addon_name
    op.prefs_tabs = 'NAMING'

    if platform.system() == 'Windows':
        op = row.operator("explorer.open_in_explorer", text="", icon='FILE_FOLDER')
        op.dirpath = collider_presets_folder()


############## OPERATORS ##############################

class EXPLORER_OT_open_folder(bpy.types.Operator):
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
    bl_label = "Naming Preset"
    preset_subdir = "collider_tools"
    preset_operator = "script.execute_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


############## PANELS ##############################

class VIEW3D_PT_collission(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collider Tools"


class VIEW3D_PT_collission_panel(VIEW3D_PT_collission):
    """Creates a Panel in the Object properties window"""
    bl_label = "Collider Tools"

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

        layout.separator()
        row = layout.row(align=True)
        row.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')

        draw_auto_convex(self, context)

        # Conversion
        # layout.separator()
        row = layout.row(align=True)
        row.label(text='Convert')

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('object.convert_to_collider', icon='PHYSICS')
        row = col.row(align=True)
        row.operator('object.convert_to_mesh', icon='MESH_MONKEY')


class VIEW3D_PT_collission_visibility_panel(VIEW3D_PT_collission):
    """Creates a Panel in the Object properties window"""

    bl_label = "Display"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('view.collider_view_material', icon='SHADING_TEXTURE', text='Materials')
        row.operator('view.collider_view_object', icon='SHADING_SOLID', text='Groups')

        row = layout.row(align=True)
        row.prop(scene, 'display_type', text='Display as')

        draw_visibility_selection_menu(context, layout)


class VIEW3D_PT_collission_material_panel(VIEW3D_PT_collission):
    """Creates a Panel in the Object properties window"""

    bl_label = "Physics Materials"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row(align=True)
        row.operator('material.create_physics_material', icon='ADD', text="Add Physics Material")

        split_left = layout.split(factor=0.65, align=True)
        col_01 = split_left.column(align=True)
        col_02 = split_left.column(align=True)

        mat = bpy.data.materials[scene.material_list_index]
        col_01.prop(mat, "name", text="")
        col_02.prop(mat, "diffuse_color", text='')

        row = layout.row(align=True)
        row.template_list("MATERIAL_UL_physics_materials", "", bpy.data, "materials", scene, "material_list_index")


class VIEW3D_PT_collission_settings_panel(VIEW3D_PT_collission):
    """Creates a Panel in the Object properties window"""

    bl_label = "Creation Settings"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Choose Naming Preset
        row = layout.row(align=True)
        row.label(text='Creation Settings')

        row = layout.row(align=True)
        row.prop(scene, "my_hide")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scene, "my_collision_shading_view")
        row = col.row(align=True)
        row.prop(scene, "wireframe_mode")
        # row = col.row(align=True)
        # row.prop(scene, "creation_mode")

        row = col.row(align=True)
        row.prop(scene, "my_space")


############## MENUS ##############################

class VIEW3D_MT_collision_creation(Menu):
    bl_label = 'Collision Creation'
    bl_ui_units_x = 45

    def draw(self, context):
        row = self.layout.row(align=True)
        row.label(text='Generation')

        row = self.layout.row(align=True)
        row.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')

        draw_auto_convex(self, context)

        self.layout.separator()
        col = self.layout.column(align=True)
        col.operator('object.convert_to_collider', icon='PHYSICS')
        col.operator('object.convert_to_mesh', icon='MESH_MONKEY')


class VIEW3D_MT_collision_visibility(Menu):
    bl_label = 'Collision Visibility'

    def draw(self, context):
        scene = context.scene

        row = self.layout.row(align=True)
        row.label(text='Display')

        self.layout.separator()
        col = self.layout.column(align=True)
        row = col.row(align=True)
        row.operator('view.collider_view_material', icon='SHADING_TEXTURE', text='Materials')
        row.operator('view.collider_view_object', icon='SHADING_SOLID', text='Groups')
        row.prop(scene, 'display_type', text='Display as')

        draw_visibility_selection_menu(context, self.layout)


class VIEW3D_MT_collision_physics_materials(Menu):
    bl_label = 'Physics Materials'

    def draw(self, context):
        scene = context.scene

        row = self.layout.row(align=True)
        row.label(text='Physics Materials')

        self.layout.separator()

        col = self.layout.column(align=True)
        row = col.row()
        row.operator('material.create_physics_material', icon='PLUS', text="Add Physics Material")
        row = col.row()
        row.template_list("MATERIAL_UL_physics_materials", "", bpy.data, "materials", scene, "material_list_index")


############## PIE ##############################

class VIEW3D_MT_PIE_template(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Collision Pie"
    bl_idname = "COLLISION_MT_pie_menu"

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

        b = split.box()
        column = b.column()
        column.menu_contents("VIEW3D_MT_collision_creation")

        # Additional Boxes in the Pie menu
        # b = box.box()
        # column = b.column()
        # column.menu_contents("VIEW3D_MT_collision_visibility")
        # b = box.box()
        # column = b.column()
        # column.menu_contents("VIEW3D_MT_collision_physics_materials")

        # North
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')

        # NorthWest
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        # NorthEast
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
