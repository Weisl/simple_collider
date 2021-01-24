from tempfile import gettempdir

import bpy
import rna_keymap_ui


class CollisionAddonPrefs(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    bl_idname = "CollisionHelpers"  ### __package__ works on multifile and __name__ not

    meshColSuffix: bpy.props.StringProperty(name="Mesh", default="_MESH")
    convexColSuffix: bpy.props.StringProperty(name="Convex Suffix", default="_CONVEX")
    boxColSuffix: bpy.props.StringProperty(name="Box Suffix", default="_BOX")
    colPreSuffix: bpy.props.StringProperty(name="Collision", default="_COL")
    colSuffix: bpy.props.StringProperty(name="Collision", default="_BOUNDING")

    executable_path: bpy.props.StringProperty(name='VHACD exe',
                                              description='Path to VHACD executable',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(
        name='Data Path',
        description='Data path to store V-HACD meshes and logs',
        default=gettempdir(),
        maxlen=1024,
        subtype='DIR_PATH'
    )

    # TODO: DELTE!
    name_template: bpy.props.StringProperty(
        name='Name Template',
        description='Name template used for generated hulls.\n? = original mesh name\n# = hull id',
        default='?_hull_#',
    )

    props = [
        "meshColSuffix",
        "convexColSuffix",
        "boxColSuffix",
        "colPreSuffix",
        "colSuffix",
    ]
    vhacd_props = [
        "executable_path",
        "data_path",
        "name_template",
    ]

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout

        for propName in self.props:
            raw = layout.row()
            raw.prop(self, propName)

        layout.separator()

        for propName in self.vhacd_props:
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
