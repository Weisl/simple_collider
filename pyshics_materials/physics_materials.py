import bpy
from bpy.types import UIList
from bpy.props import StringProperty

from .material_functions import set_material, remove_materials

class MATERIAL_OT_set_physics_material(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "material.set_physics_material"
    bl_label = "Set Physics Material"

    physics_material_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        for obj in context.selected_objects:
            try:
                mat = bpy.data.materials[self.physics_material_name]
                remove_materials(obj)
                set_material(obj, mat)
            except:
                print('ERROR')
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

    export : bpy.props.BoolProperty(name="Export", default=False)

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scn = context.scene
        mat = item
        self.filter_name = scn.PhysicsIdentifier
        self.name_ob = item.name

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if mat:
                # Multi prop edit (Checkbox: which mats should be edited)
                # row.prop(mat, "edit", text="")

                row = layout.row(align=True)
                lb = row.label(text=mat.name)
                op2 = row.operator('material.set_physics_material', text='', icon='MATERIAL')
                op2.physics_material_name = mat.name
                row.prop(mat, "diffuse_color", text='')
        return