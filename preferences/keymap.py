import bpy

keys = []

def add_keymap():
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name="Window")
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences

    kmi = km.keymap_items.new(idname='wm.call_menu_pie', type=prefs.collision_pie_type, value='PRESS', ctrl=prefs.collision_pie_ctrl, shift=prefs.collision_pie_shift, alt=prefs.collision_pie_alt)
    add_key_to_keymap("COLLISION_MT_pie_menu", kmi, km)
    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True)
    add_key_to_keymap('VIEW3D_PT_collission_visibility_panel', kmi, km)
    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True, ctrl=True)
    add_key_to_keymap('VIEW3D_PT_collission_material_panel', kmi, km)


def add_key_to_keymap(idname, kmi, km):
    kmi.properties.name = idname
    kmi.active = True
    keys.append((km, kmi))

def remove_keymap():
    # only works for menues and pie menus
    for km, kmi in keys:
        if hasattr(kmi.properties, 'name') and kmi.properties.name in ['COLLISION_MT_pie_menu', 'VIEW3D_PT_collission_visibility_panel', 'VIEW3D_PT_collission_material_panel']:
            km.keymap_items.remove(kmi)
    keys.clear()
    
def remove_key(context, idname, properties_name):
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps["Window"]
    
    for kmi in km.keymap_items:
        if kmi.idname == idname and kmi.properties.name == properties_name :
            km.keymap_items.remove(kmi)

class REMOVE_OT_hotkey(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "collision.remove_hotkey"
    bl_label = "Remove hotkey"
    bl_description = "Remove hotkey"
    bl_options = {'REGISTER','INTERNAL'}

    idname: bpy.props.StringProperty()
    properties_name: bpy.props.StringProperty()

    def execute(self, context):
        remove_key(context, self.idname, self.properties_name)

        prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        prefs.collision_pie_type = ""
        prefs.collision_pie_ctrl = False
        prefs.collision_pie_shift = False
        prefs.collision_pie_alt = False

        return {'FINISHED'}