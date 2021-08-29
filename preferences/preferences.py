from tempfile import gettempdir

import bpy
import rna_keymap_ui
from .naming_preset import COLLISION_preset
from .naming_preset import OBJECT_MT_collision_presets

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

        row = layout.row(align=True)
        row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)
        row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
        row.operator(COLLISION_preset.bl_idname, text="", icon='REMOVE').remove_active = True

        for propName in self.props:
            raw = layout.row()
            raw.prop(self, propName)

        layout.separator()

        for propName in self.vhacd_props:
            raw = layout.row()
            raw.prop(self, propName)

        ''' KEYMAP UI '''
        box = layout.box()
        col = box.column()
        col.label(text="keymap")

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps['3D View']

        kmis = []

        row = layout.row()
        row.operator("wm.url_open", text="Open Link").url = "https://github.com/kmammou/v-hacd"




        from .keymap import get_hotkey_entry_item
        # Menus and Pies
        kmis.append(get_hotkey_entry_item(km, 'wm.call_menu_pie', 'COLLISION_MT_pie_menu'))

        for kmi in kmis:
            if kmi:
                col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

            else:
                col.label(text="No hotkey entry found")
                col.operator("cam_manager.add_hotkey", text="Add hotkey entry", icon='ADD')

