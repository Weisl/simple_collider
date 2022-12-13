import bpy

# addon_keymaps = []


# def remove_hotkey():
#     ''' Clears custom hotkeys stored in addon_keymaps '''

#     # only works for menues and pie menus
#     for km, kmi in addon_keymaps:
#         if hasattr(kmi.properties, 'name'):
#             if kmi.properties.name in ['COLLISION_MT_pie_menu', 'VIEW3D_PT_collission_visibility_panel',
#                                        'VIEW3D_PT_collission_material_panel']:
#                 km.keymap_items.remove(kmi)

#     addon_keymaps.clear()


# def add_hotkey(context=None):
#     ''' Add default hotkey configuration'''
#     if not context:
#         context = bpy.context

#     wm = bpy.context.window_manager
#     kc = wm.keyconfigs.addon

#     if kc:
#         km = kc.keymaps.new(name="3D View", space_type='VIEW_3D', region_type='WINDOW')
#         kmi = km.keymap_items.new(idname='wm.call_menu_pie', type='C', value='PRESS', ctrl=True, shift=True)
#         kmi.properties.name = "COLLISION_MT_pie_menu"
#         kmi.active = True
#         addon_keymaps.append((km, kmi))

#         km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D', region_type='WINDOW')
#         kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True)
#         kmi.properties.name = 'VIEW3D_PT_collission_visibility_panel'
#         kmi.active = True
#         addon_keymaps.append((km, kmi))

#         km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D', region_type='WINDOW')
#         kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True, ctrl=True)
#         kmi.properties.name = 'VIEW3D_PT_collission_material_panel'
#         kmi.active = True
#         addon_keymaps.append((km, kmi))


# def get_hotkey_entry_item(km, kmi_name, kmi_value=None):
#     ''' Returns hotkey of specific type, with specific properties.name (keymap is not a dict, so referencing by keys is not enough
#     if there are multiple hotkeys!)'''
#     # for menus and pie_menu
#     if kmi_value:
#         for i, km_item in enumerate(km.keymap_items):
#             if km.keymap_items.keys()[i] == kmi_name:
#                 if km.keymap_items[i].properties.name == kmi_value:
#                     return km_item

#     # for collider_shapes
#     else:
#         if km.keymap_items.get(kmi_name):
#             return km.keymap_items.get(kmi_name)

#     return None



def get_hotkey_entry_item(km, kmi_name, kmi_value, properties):
    for i, km_item in enumerate(km.keymap_items):
        if km.keymap_items.keys()[i] == kmi_name:
            if properties == 'name':
                if km.keymap_items[i].properties.name == kmi_value:
                    return km_item
            elif properties == 'tab':
                if km.keymap_items[i].properties.tab == kmi_value:
                    return km_item
            elif properties == 'none':
                return km_item
    return None


# class COLLISION_OT_add_hotkey_renaming(bpy.types.Operator):
#     ''' Add hotkey entry '''
#     bl_idname = "collision_tool.add_hotkey"
#     bl_label = "Addon preferences Example"
#     bl_options = {'REGISTER', 'INTERNAL'}

#     def execute(self, context):
#         add_hotkey(context)
#         return {'FINISHED'}
