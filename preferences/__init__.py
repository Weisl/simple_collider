import bpy

from . import keymap
from . import naming_preset
from . import preferences
from . import properties
from .properties import ColliderTools_Properties
from .preferences import update_panel_category


keys = []


def add_hotkey():
    wm = bpy.context.window_manager
    addon_keyconfig = wm.keyconfigs.user
    # addon_keyconfig = wm.keyconfigs.active
    kc = addon_keyconfig
    
    if not kc:
        print('Collider Tools: keyconfig unavailable (in batch mode?), no keybinding items registered')
        return

    # register to 3d view mode tab
    km = kc.keymaps.new(name="3D View Generic", space_type="VIEW_3D")

    kmi = km.keymap_items.new(idname='wm.call_menu_pie', type='C', value='PRESS', ctrl=True, shift=True)
    kmi.properties.name = "COLLISION_MT_pie_menu"
    kmi.active = True
    
    keys.append((km, kmi))

    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True)
    kmi.properties.name = 'VIEW3D_PT_collission_visibility_panel'
    kmi.active = True
    
    keys.append((km, kmi))
    
    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True, ctrl=True)
    kmi.properties.name = 'VIEW3D_PT_collission_material_panel'
    kmi.active = True
    
    keys.append((km, kmi))



def remove_hotkey():
    ''' Clears custom hotkeys stored in addon_keymaps '''

    # only works for menues and pie menus
    for km, kmi in keys:
        if hasattr(kmi.properties, 'name') and kmi.properties.name in ['COLLISION_MT_pie_menu', 'VIEW3D_PT_collission_visibility_panel', 'VIEW3D_PT_collission_material_panel']:
            km.keymap_items.remove(kmi)
    keys.clear()


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
    
class COLLISION_OT_add_hotkey_renaming(bpy.types.Operator):
    ''' Add hotkey entry '''
    bl_idname = "collision_tool.add_hotkey"
    bl_label = "Addon preferences Example"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        add_hotkey()
        return {'FINISHED'}

# keymap needs to be registered before the preferences UI
classes = (
    properties.ColliderTools_Properties,
    naming_preset.COLLISION_preset,
    COLLISION_OT_add_hotkey_renaming,
    preferences.CollisionAddonPrefs,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls) 
    
    update_panel_category(None, bpy.context)

    # Pointer Properties have to be initialized after classes
    scene = bpy.types.Scene
    scene.collider_tools = bpy.props.PointerProperty(type=ColliderTools_Properties)

    add_hotkey()


    

def unregister():
    from bpy.utils import unregister_class

    remove_hotkey()

    for cls in reversed(classes):
        unregister_class(cls)
        
    scene = bpy.types.Scene
    del scene.collider_tools
