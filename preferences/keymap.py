import bpy

from .. import __package__ as base_package

keymaps_items_dict = {"Collider Pie Menu": {"name": 'collision_pie', "idname": 'wm.call_menu_pie',
                                            "operator": 'COLLISION_MT_pie_menu', "type": 'C',
                                            "value": 'PRESS', "ctrl": True, "shift": True, "alt": False,
                                            "active": True},
                      "Visibility Menu": {"name": 'collision_visibility', "idname": 'wm.call_panel',
                                          "operator": 'VIEW3D_PT_collision_visibility_panel', "type": 'P',
                                          "value": 'PRESS', "ctrl": False, "shift": True, "alt": False,
                                          "active": True},
                      "Material Menu": {"name": 'collision_material', "idname": 'wm.call_panel',
                                        "operator": 'VIEW3D_PT_collision_material_panel', "type": 'P',
                                        "value": 'PRESS', "ctrl": True, "shift": True, "alt": False,
                                        "active": True},
                      }


def add_key(context, idname, type, ctrl, shift, alt, operator, active):
    wm = context.window_manager
    addon_km = wm.keyconfigs.active.keymaps.get('3D View')
    if not addon_km:
        addon_km = wm.keyconfigs.active.keymaps.new(name="3D View")
    kmi = addon_km.keymap_items.new(idname=idname, type=type, value='PRESS', ctrl=ctrl, shift=shift, alt=alt)
    if operator != '':
        kmi.properties.name = operator
    kmi.active = active


def remove_key(context, idname, properties_name):
    """Removes addon hotkeys from the keymap"""
    wm = context.window_manager
    addon_km = wm.keyconfigs.active.keymaps.get('3D View')
    if not addon_km:
        return
    items_to_remove = []
    for kmi in addon_km.keymap_items:
        if properties_name:
            if kmi.idname == idname and hasattr(kmi.properties, 'name') and kmi.properties.name == properties_name:
                items_to_remove.append(kmi)
        else:
            if kmi.idname == idname:
                items_to_remove.append(kmi)
    for kmi in items_to_remove:
        addon_km.keymap_items.remove(kmi)


def add_keymap():
    context = bpy.context
    prefs = context.preferences.addons[base_package].preferences
    wm = context.window_manager
    addon_km = wm.keyconfigs.active.keymaps.get('3D View')
    if not addon_km:
        addon_km = wm.keyconfigs.active.keymaps.new(name="3D View")

    # Remove existing keymap items for this addon
    for kmi in addon_km.keymap_items[:]:
        for key, valueDic in keymaps_items_dict.items():
            idname = valueDic["idname"]
            operator = valueDic["operator"]
            if kmi.idname == idname and (
                    not operator or (hasattr(kmi.properties, 'name') and kmi.properties.name == operator)):
                addon_km.keymap_items.remove(kmi)

    # Add new keymap items
    for key, valueDic in keymaps_items_dict.items():
        idname = valueDic["idname"]
        type = getattr(prefs, f'{valueDic["name"]}_type')
        ctrl = getattr(prefs, f'{valueDic["name"]}_ctrl')
        shift = getattr(prefs, f'{valueDic["name"]}_shift')
        alt = getattr(prefs, f'{valueDic["name"]}_alt')
        operator = valueDic["operator"]
        active = valueDic["active"]

        # Skip if no key is assigned
        if type == 'NONE':
            continue

        add_key(context, idname, type, ctrl, shift, alt, operator, active)


def remove_keymap():
    wm = bpy.context.window_manager
    addon_km = wm.keyconfigs.active.keymaps.get('3D View')
    if not addon_km:
        return
    items_to_remove = []
    for kmi in addon_km.keymap_items:
        for key, valueDic in keymaps_items_dict.items():
            idname = valueDic["idname"]
            operator = valueDic["operator"]
            if kmi.idname == idname and (
                    not operator or (hasattr(kmi.properties, 'name') and kmi.properties.name == operator)):
                items_to_remove.append(kmi)
    for kmi in items_to_remove:
        addon_km.keymap_items.remove(kmi)


class SIMPLE_COLLISION_OT_remove_hotkey(bpy.types.Operator):
    """Remove a hotkey and reset its properties"""
    bl_idname = "collision.remove_hotkey"
    bl_label = "Remove Hotkey"
    bl_description = "Remove the hotkey and reset its properties"
    bl_options = {'REGISTER', 'INTERNAL'}

    idname: bpy.props.StringProperty()
    properties_name: bpy.props.StringProperty()
    property_prefix: bpy.props.StringProperty()

    def execute(self, context):
        remove_key(context, self.idname, self.properties_name)
        prefs = context.preferences.addons[base_package].preferences
        setattr(prefs, f'{self.property_prefix}_type', "NONE")
        setattr(prefs, f'{self.property_prefix}_ctrl', False)
        setattr(prefs, f'{self.property_prefix}_shift', False)
        setattr(prefs, f'{self.property_prefix}_alt', False)
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class SIMPLE_COLLISION_OT_change_hotkey(bpy.types.Operator):
    """UI button to assign a new key to an addon hotkey"""
    bl_idname = "collision.key_selection_button"
    bl_label = "Press the button you want to assign to this operation."
    bl_options = {'REGISTER', 'INTERNAL'}

    property_prefix: bpy.props.StringProperty()

    def invoke(self, context, event):
        prefs = context.preferences.addons[base_package].preferences
        self.prefs = prefs
        setattr(prefs, f'{self.property_prefix}_type', "NONE")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.my_event = 'NONE'
        if event.type and event.value == 'RELEASE':
            self.my_event = event.type
            setattr(self.prefs, f'{self.property_prefix}_type', self.my_event)
            self.execute(context)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.report({'INFO'}, "Key change: " + bpy.types.Event.bl_rna.properties['type'].enum_items[self.my_event].name)
        return {'FINISHED'}


classes = (
    SIMPLE_COLLISION_OT_remove_hotkey,
    SIMPLE_COLLISION_OT_change_hotkey,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_keymap()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    remove_keymap()
