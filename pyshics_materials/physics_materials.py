import bpy
from bpy.props import StringProperty
from bpy.types import UIList

from .material_functions import set_physics_material, remove_materials, create_material


class MATERIAL_OT_physics_material_create(bpy.types.Operator):
    # Creates Master asset structure: a master empty with different sub empties than can be definied by the technical artist in the .... .
    # Asset Type - Enum defines in AssetName
    # Asset Location - Enum defined in AssetLocation
    # Asset Category - Enum defined in AssetCategory
    # BaseName - Name of the new asset
    # EmptySize - representation size of the empty

    bl_idname = "material.create_physics_material"
    bl_label = "Create Physics Material"
    bl_description = "Create Physics Material"
    bl_options = {'REGISTER', 'UNDO'}

    my_baseName: bpy.props.StringProperty(name="Name")
    rgb_controller: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', default=(1, 1, 1, 0.5), size=4, min=0,
                                                  max=1, description="Display Color")

    def invoke(self, context, event):

        # get preset Values
        # Custom addon Props
        try:
            prefs = context.preferences.addons[__package__.split('.')[0]].preferences
            # self.my_baseName = prefs.physics_material_name
        except:
            pass
        else:
            return context.window_manager.invoke_props_dialog(self)
        return {'CANCELLED'}

    def execute(self, context):
        physics_material = create_material(self.my_baseName, self.rgb_controller)
        return {"FINISHED"}


class MATERIAL_OT_set_physics_material(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "material.set_physics_material"
    bl_label = "Set Physics Material"
    bl_options = {'REGISTER', 'UNDO'}

    physics_material_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        for obj in context.selected_objects:
            try:
                remove_materials(obj)
                set_physics_material(obj, self.physics_material_name)

            except Exception as e:
                print('ERROR assigning physics material: ' + str(e))

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

        if self.set_initial_state:
            prefs = context.preferences.addons[__package__.split('.')[0]].preferences

            self.filter_name = prefs.physics_material_filter
            self.set_initial_state = False

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if mat:
                # Multi prop edit (Checkbox: which mats should be edited)
                # row.prop(mat, "edit", text="")

                row = layout.row(align=True)
                row.label(text=mat.name)
                row.operator('material.set_physics_material', text='', icon='MATERIAL').physics_material_name = mat.name
                row.prop(mat, "diffuse_color", text='')
        return

    def draw_filter(self, context, layout):
        # Nothing much to say here, it's usual UI code...
        row = layout.row()
        row.prop(self, "filter_name", text="Filter", )
