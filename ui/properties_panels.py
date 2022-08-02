from bpy.types import Panel
import textwrap
import bpy



visibility_operators = {
    'ALL_COLLIDER': 'All Colliders',
    'SIMPLE': 'Simple',
    'COMPLEX': 'Complex',
    'SIMPLE_COMPLEX':'Simple and Complex',
    'OBJECTS': "Objects",
}

def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)   # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)

class PREFERENCES_OT_open_addon(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "preferences.addon_search"
    bl_label = "Open Addon preferences"

    addon_name: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.screen.userpref_show()
        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = self.addon_name
        prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        prefs.prefs_tabs = 'VHACD'
        # bpy.ops.preferences.addon_expand(module=self.addon_name)
        return {'FINISHED'}

def draw_visibility_selection_menu(layout):
    split_left = layout.split(factor=0.35)
    col_01 = split_left.column()
    col_02 = split_left.column()

    layout = layout
    show_icon = 'HIDE_OFF'
    hide_icon = 'HIDE_ON'
    show_text = ''
    hide_text = ''

    select_icon = 'NONE'
    deselect_icon = 'NONE'
    select_text = 'Select'
    deselect_text = 'Deselect'

    delete_icon = 'TRASH'
    delete_text = ''

    row = col_01.row(align=True)
    row.label(text=visibility_operators['ALL_COLLIDER'])

    row = col_02.row(align=True)
    op = row.operator("object.all_show_collisions", icon=show_icon, text=show_text)
    op.hide = False
    op.mode = 'ALL_COLLIDER'
    op = row.operator("object.all_hide_collisions", icon=hide_icon, text=hide_text)
    op.hide = True
    op.mode = 'ALL_COLLIDER'
    op = row.operator("object.all_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = 'ALL_COLLIDER'
    op = row.operator("object.all_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = 'ALL_COLLIDER'
    op = row.operator("object.all_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = 'ALL_COLLIDER'

    row = col_01.row(align=True)
    row.label(text=visibility_operators['SIMPLE'])

    row = col_02.row(align=True)
    op = row.operator("object.simple_show_collisions", icon=show_icon, text=show_text)
    op.hide = False
    op.mode = 'SIMPLE'
    op = row.operator("object.simple_hide_collisions", icon=hide_icon, text=hide_text)
    op.hide = True
    op.mode = 'SIMPLE'
    op = row.operator("object.simple_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = 'SIMPLE'
    op = row.operator("object.simple_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = 'SIMPLE'
    op = row.operator("object.simple_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = 'SIMPLE'

    row = col_01.row(align=True)
    row.label(text=visibility_operators['COMPLEX'])
    row = col_02.row(align=True)
    op = row.operator("object.complex_show_collisions", icon=show_icon, text=show_text)
    op.hide = False
    op.mode = 'COMPLEX'
    op = row.operator("object.complex_hide_collisions", icon=hide_icon, text=hide_text)
    op.hide = True
    op.mode = 'COMPLEX'
    op = row.operator("object.complex_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = 'COMPLEX'
    op = row.operator("object.complex_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = 'COMPLEX'
    op = row.operator("object.simple_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = 'COMPLEX'

    row = col_01.row(align=True)
    row.label(text=visibility_operators['SIMPLE_COMPLEX'])
    row = col_02.row(align=True)
    op = row.operator("object.simple_complex_show_collisions", icon=show_icon, text=show_text)
    op.hide = False
    op.mode = 'SIMPLE_COMPLEX'
    op = row.operator("object.simple_complex_hide_collisions", icon=hide_icon, text=hide_text)
    op.hide = True
    op.mode = 'SIMPLE_COMPLEX'
    op = row.operator("object.simple_complex_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = 'SIMPLE_COMPLEX'
    op = row.operator("object.simple_complex_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = 'SIMPLE_COMPLEX'
    op = row.operator("object.simple_complex_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = 'SIMPLE_COMPLEX'


    row = col_01.row(align=True)
    row.label(text=visibility_operators['OBJECTS'])
    row = col_02.row(align=True)
    op = row.operator("object.non_collider_show_collisions", icon=show_icon, text=show_text)
    op.hide = False
    op.mode = 'OBJECTS'
    op = row.operator("object.non_collider_hide_collisions", icon=hide_icon, text=hide_text)
    op.hide = True
    op.mode = 'OBJECTS'
    op = row.operator("object.non_collider_select_collisions", icon=select_icon, text=select_text)
    op.select = True
    op.mode = 'OBJECTS'
    op = row.operator("object.non_collider_deselect_collisions", icon=deselect_icon, text=deselect_text)
    op.select = False
    op.mode = 'OBJECTS'
    op = row.operator("object.non_collider_delete_collisions", icon=delete_icon, text=delete_text)
    op.mode = 'OBJECTS'


class VIEW3D_PT_collission_panel(Panel):
    """Creates a Panel in the Object properties window"""

    bl_label = "Collider Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collider Tools"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        scene = context.scene

        # Visibillity and Selection
        layout.separator()

        row = layout.row(align=True)
        row.label(text='Visibility and Selection')

        draw_visibility_selection_menu(layout)

        # Physics Materials
        layout.separator()

        row = layout.row()
        row.label(text='Physics Material')

        row = layout.row()
        row.prop(scene, "PhysicsIdentifier", text='Filter')

        row = layout.row()
        row.prop(scene, "CollisionMaterials", text="")

        # Create Collider
        layout.separator()

        row = layout.row(align=True)
        row.label(text='Add Collider')
        row = layout.row(align=True)
        row.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        row = layout.row(align=True)
        row.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')
        row = layout.row(align=True)
        row.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')
        row = layout.row(align=True)
        row.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')
        row = layout.row(align=True)
        row.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
        row = layout.row(align=True)
        row.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        #special Collider Creation
        layout.separator()

        row = layout.row(align=True)
        row.label(text='Auto Convex')

        row = layout.row()
        row.prop(scene, 'convex_decomp_depth')
        row = layout.row()
        row.prop(scene, 'maxNumVerticesPerCH')


        prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        row = layout.row(align=True)

        if prefs.executable_path:
            row.operator("collision.vhacd", text="Auto Convex", icon='MESH_ICOSPHERE')
        else:
            from .. import bl_info
            row.operator("preferences.addon_search", text="Install V-HACD", icon='ERROR').addon_name = bl_info["name"]

        # Conversion
        layout.separator()
        row = layout.row(align=True)
        row.label(text='Convert')

        row = layout.row(align=True)
        row.operator('object.convert_to_collider', icon='PHYSICS')
        row = layout.row(align=True)
        row.operator('object.convert_to_mesh', icon='MESH_MONKEY')
        row = layout.row()
        row.prop(scene, "DefaultMeshMaterial", text='Material')


