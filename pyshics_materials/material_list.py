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
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    MAT_FILTER = 1 << 0

    set_initial_state: bpy.props.BoolProperty(default=True)

    def filter_list(self, context):
        '''
        Filter physics material by tag
        :param self:
        :param context:
        :return: flt_flags is a bit-flag containing the filtering and flt
                flt_neworder defines the order of all cameras
        '''

        helper_funcs = bpy.types.UI_UL_list

        # Default return values.
        flt_flags = []
        flt_neworder = []

        # Get all objects from scene.
        materials = bpy.data.materials

        # Create bitmask for all objects
        flt_flags = [self.bitflag_filter_item] * len(materials)

        # Filter by object type.
        for idx, mat in enumerate(materials):
            #filter out greace pencil objects
            if self.filter_name not in mat.name:
                flt_flags[idx] &= ~self.bitflag_filter_item
            elif mat.is_grease_pencil == True:
                flt_flags[idx] &= ~self.bitflag_filter_item
            # filter materials not tagged as physics materials
            elif mat.isPhysicsMaterial == False and context.scene.use_physics_tag == True:
                flt_flags[idx] &= ~self.bitflag_filter_item
            # items that get shown
            else:
                flt_flags[idx] |= self.MAT_FILTER

        flt_neworder = helper_funcs.sort_items_by_name(materials, "name")

        return flt_flags, flt_neworder

    def filter_items(self, context, data, propname):
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown), and 31 other bits are free for custom needs. Here we use the
        #   first one to mark MAT_FILTER.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).
        flt_flags, flt_neworder = self.filter_list(context)
        return flt_flags, flt_neworder

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

                if context.scene.use_physics_tag == False:
                    tagIcon = 'SOLO_ON' if mat.isPhysicsMaterial else 'SOLO_OFF'
                    row.prop(mat, 'isPhysicsMaterial', text='', icon=tagIcon)
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
