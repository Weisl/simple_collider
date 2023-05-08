import bpy
from bpy.types import UIList
from .material_functions import set_active_physics_material

class BUTTON_OP_set_active_physics_material(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "material.set_active_physics_material"
    bl_label = "Simple Object Operator"

    mat_name : bpy.props.StringProperty()

    def execute(self, context):
        print(self.mat_name)
        set_active_physics_material(context, self.mat_name)
        return {'FINISHED'}


class MATERIAL_UL_physics_materials(UIList):
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.

    set_initial_state: bpy.props.BoolProperty(default=True)

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mat = item
        self.use_filter_show = True

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if self.set_initial_state:
                prefs = context.preferences.addons[__package__.split('.')[0]].preferences
                self.filter_name = prefs.physics_material_filter

                self.set_initial_state = False

            if mat and self.layout_type in {'DEFAULT', 'COMPACT'}:
                row = layout.row(align=True)

                if mat.is_grease_pencil == True:
                    row.enabled = False

                else:  # mat.is_grease_pencil == False:
                    row.prop(mat, 'isPhysicsMaterial', text='')
                    row.operator('material.set_physics_material', text='',
                                 icon='FORWARD').physics_material_name = mat.name

                # row.prop(mat, "name", text="", emboss=False, icon_value=icon)
                op = row.operator('material.set_active_physics_material', text=mat.name, icon_value=icon)
                op.mat_name = mat.name

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

        return

    def draw_filter(self, context, layout):
        # Nothing much to say here, it's usual UI code...
        scene = context.scene

        row = layout.row()
        row.prop(self, "filter_name", text="Filter", )
        row = layout.row()
        row.prop(scene, "use_physics_tag", icon="SOLO_ON")
