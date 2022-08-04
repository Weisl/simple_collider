import bpy
from bpy.types import UIList

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
    # Test to create renamint in table
    #stringTest = bpy.props.StringProperty(name = "Name",update = testUpdate(), get = testGetAsset, set = testSetAsset)

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scn = context.scene
        mat = item
        self.filter_name = scn.PhysicsIdentifier
        self.name_ob = item.name

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if mat:
                row = layout.row(align = True)
                lb = row.label(text=mat.name)

                # icon = 'ERROR'
                # if obj.get('isAsset') is not None and obj.type == 'EMPTY':
                #     icon = 'FILE_TICK'

                # split = layout.split(factor = 0.5)
                # split.prop(item, "manipulate", text = "")
                # split = layout.split(factor = 0.8)
                # split.operator('assetmanager.select_item', text = mat.name, icon = 'OBJECT_DATA').name = mat.name
                # row = split.row(align = True)
                #row.operator('assetmanager.select_item', text = '', icon = 'OBJECT_DATA').name = item.name
                # op1 = row.operator('assetmanager.select_hierarchy', text = '', icon = 'COLLAPSEMENU')
                # op1.my_assetName = mat.name
                # op2 = row.operator('master.asset_rename', text = '', icon = 'FILE_FONT')
                # op2.my_assetName = mat.name
                # op3 = row.operator('assetmanager.asset_local_singleview', text = '', icon = 'SOLO_ON')
                # op3.my_assetName = mat.name
        return