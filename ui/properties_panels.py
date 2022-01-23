from bpy.types import Panel
import textwrap
import bpy



visibility_operators = {
    'ALL_COLLIDER': 'All Collider',
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


class CollissionPanel(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Collider Tools"
    bl_idname = "COLLISION_PT_Create"
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


        # for value in visibility_operators:
        #     col.label(text=value)

        for key, value in visibility_operators.items():
            row = layout.row(align=True)
            label = row.label(text=key)
            op = row.operator("object.hide_collisions", icon='HIDE_OFF', text='')
            op.hide = False
            op.mode = key
            op = row.operator("object.hide_collisions", icon='HIDE_ON', text='')
            op.hide = True
            op.mode = key
            op = row.operator("object.select_collisions", icon='RESTRICT_SELECT_OFF', text='')
            op.select = True
            op.mode = key
            op = row.operator("object.select_collisions", icon='RESTRICT_SELECT_ON', text='')
            op.select = False
            op.mode = key

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


