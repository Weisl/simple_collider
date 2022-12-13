import bpy

from . import keymap
from . import naming_preset
from . import preferences
from . import properties
from .properties import ColliderTools_Properties
# from .keymap import add_hotkey, remove_hotkey
from .preferences import update_panel_category

# keymap needs to be registered before the preferences UI
classes = (
    properties.ColliderTools_Properties,
    naming_preset.COLLISION_preset,
    # keymap.COLLISION_OT_add_hotkey_renaming,
    preferences.CollisionAddonPrefs,
)

keys = []

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls) 
    
    update_panel_category(None, bpy.context)

    # Pointer Properties have to be initialized after classes
    scene = bpy.types.Scene
    scene.collider_tools = bpy.props.PointerProperty(type=ColliderTools_Properties)

    # add_hotkey()
    wm = bpy.context.window_manager
    active_keyconfig = wm.keyconfigs.active
    addon_keyconfig = wm.keyconfigs.addon
    kc = addon_keyconfig
    
    if not kc:
        print('Collider Tools: keyconfig unavailable (in batch mode?), no keybinding items registered')
        return


    # register to 3d view mode tab
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

    kmi = km.keymap_items.new(idname='wm.call_menu_pie', type='C', value='PRESS', ctrl=True, shift=True)
    kmi.properties.name = "COLLISION_MT_pie_menu"
    keys.append((km, kmi))

    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True)
    kmi.properties.name = 'VIEW3D_PT_collission_visibility_panel'
    keys.append((km, kmi))
    
    kmi = km.keymap_items.new(idname='wm.call_panel', type='P', value='PRESS', shift=True, ctrl=True)
    kmi.properties.name = 'VIEW3D_PT_collission_material_panel'
    keys.append((km, kmi))
    
    del active_keyconfig
    del addon_keyconfig

    

def unregister():
    from bpy.utils import unregister_class

    # remove_hotkey()
    keys.clear()

    for cls in reversed(classes):
        unregister_class(cls)
