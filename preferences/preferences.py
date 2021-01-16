import bpy


class CollisionAddonPrefs(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__  ### __package__ works on multifile and __name__ not

    meshColSuffix: bpy.props.StringProperty(name="Mesh", default="_MESH")
    convexColSuffix: bpy.props.StringProperty(name="Convex Suffix", default="_CONVEX")
    boxColSuffix: bpy.props.StringProperty(name="Box Suffix", default="_BOX")
    colPreSuffix: bpy.props.StringProperty(name="Collision", default="_COL")
    colSuffix: bpy.props.StringProperty(name="Collision", default="_BOUNDING_")

    props = [
        "meshColSuffix",
        "convexColSuffix",
        "boxColSuffix",
        "colPreSuffix",
        "colSuffix",
    ]

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout
        for propName in self.props:
            raw = layout.row()
            raw.prop(self, propName)


        box = layout.box()
        col = box.column()

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps['3D View']

        from .keymap import get_hotkey_entry_item

        kmis = []
        kmis.append(get_hotkey_entry_item(km, 'wm.call_panel', 'COLLISION_PT_Create'))

        for kmi in kmis:
            if kmi:
                col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
            else:
                col.label(text="No hotkey entry found")
                col.operator("utilities.add_hotkey", text="Add hotkey entry", icon='ADD')