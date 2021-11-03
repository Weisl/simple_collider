from tempfile import gettempdir

import bpy
import rna_keymap_ui
from .naming_preset import COLLISION_preset
from .naming_preset import OBJECT_MT_collision_presets

#
# collider_shapes = {
#     "boxColSuffix": {'shape': "BOX", 'label': 'Box Collider', 'default_naming': 'Box'},
#     "sphereColSuffix": {'shape': "SPHERE", 'label': 'Sphere Collider', 'default_naming': 'Sphere'},
#     "convexColSuffix": {'shape': "CONVEX", 'label': 'Convex Collider', 'default_naming': 'Convex'},
#     "meshColSuffix": {'shape': "MESH", 'label': 'Triangle Mesh Collider', 'default_naming': 'Mesh'},
# }


class CollisionAddonPrefs(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    bl_idname = "CollisionHelpers"  ### __package__ works on multifile and __name__ not

    prefs_tabs: bpy.props.EnumProperty(
        items=(('NAMING', "Naming", "NAMING"), ('KEYMAP', "Keymap", "Keymap"), ('VHACD', "Vhacd", "VHACD")),
        default='NAMING')

    naming_position: bpy.props.EnumProperty(
        items=(('PREFIX', "Prefix", "Prefix"), ('SUFFIX', "Suffix", "Suffix")),
        default='SUFFIX')

    separator: bpy.props.StringProperty(name="Separator ", default="_")
    colPreSuffix: bpy.props.StringProperty(name="Collision ", default="COL")
    optionalSuffix: bpy.props.StringProperty(name="Additional Suffix (optional)", default="")
    colSuffix: bpy.props.StringProperty(name="Non Collision", default="BOUNDING")

    basename: bpy.props.StringProperty(name="Collider Base Name", default="geo")

    colAll: bpy.props.StringProperty(name="All Collisions", default="ALL")
    colSimple: bpy.props.StringProperty(name="Simple Collisions", default="SIMPLE")
    colComplex: bpy.props.StringProperty(name="Complex Collisions", default="COMPLEX")

    # Collider Shapes
    boxColSuffix: bpy.props.StringProperty(name="Box Collision", default="BOX")
    convexColSuffix: bpy.props.StringProperty(name="Convex Collision", default="CONVEX")
    sphereColSuffix: bpy.props.StringProperty(name="Sphere Collision", default="SPHERE")
    meshColSuffix: bpy.props.StringProperty(name="Mesh Collision", default="MESH")

    executable_path: bpy.props.StringProperty(name='VHACD exe',
                                              description='Path to VHACD executable',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    use_col_Complexity: bpy.props.BoolProperty(
        name = 'Use Complexity',
        description = 'Use Complexity',
        default = True
    )

    my_color_all: bpy.props.FloatVectorProperty(name="All Collider", description="",
                                                default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
                                                subtype='COLOR', size=4)

    my_color_simple: bpy.props.FloatVectorProperty(name="Simple Collider", description="",
                                                   default=(0.5, 1, 0.36, 0.25), min=0.0, max=1.0,
                                                   subtype='COLOR', size=4)

    my_color_complex: bpy.props.FloatVectorProperty(name="Complex Collider", description="",
                                                    default=(1, 0.36, 0.36, 0.25), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_color: bpy.props.FloatVectorProperty(name="Font Color", description="",
                                                    default=(1, 1, 1, 1), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)
    modal_font_color_02: bpy.props.FloatVectorProperty(name="Font Color", description="",
                                                    default=(1, 1, 1, 1), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)
    modal_font_color_03: bpy.props.FloatVectorProperty(name="Font Color", description="",
                                                    default=(1, 1, 1, 1), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_size: bpy.props.IntProperty(name='Font Size', description="", default=72)

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

    use_col_collection: bpy.props.BoolProperty(
        name = 'Use Col Collection',
        description = 'Add all collisions to a Collision Collection',
        default = True
    )

    use_parent_name: bpy.props.BoolProperty(
        name = 'Name from parent',
        description = 'Use Parent name for collider name',
        default = True
    )

    col_collection_name: bpy.props.StringProperty(
        name='Collection Name',
        description='',
        default='Col'
    )
    props = [
        "use_parent_name",
        "basename",
        "meshColSuffix",
        "convexColSuffix",
        "boxColSuffix",
        "sphereColSuffix",
        "colPreSuffix",
        "colSuffix",
        "optionalSuffix",
        "colAll",
        "colSimple",
        "colComplex",
        "modal_font_color",
        "use_col_collection",
        "col_collection_name",
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
        row.prop(self, "prefs_tabs", expand=True)



        if self.prefs_tabs == 'NAMING':
            row = layout.row(align=True)
            row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)
            row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
            row.operator(COLLISION_preset.bl_idname, text="", icon='REMOVE').remove_active = True

            row = layout.row(align=True)
            row.prop(self, "use_col_Complexity")

            row = layout.row()
            row.prop(self, "naming_position", text='Collider Naming', expand=True)

            for propName in self.props:
                row = layout.row()
                row.prop(self, propName)

            layout.separator()
            row = layout.row()
            row.prop(self, 'my_color_all')
            row = layout.row()
            row.prop(self, 'my_color_simple')
            row = layout.row()
            row.prop(self, 'my_color_complex')



        elif self.prefs_tabs == 'KEYMAP':

            box = layout.box()
            col = box.column()
            col.label(text="keymap")

            wm = context.window_manager
            kc = wm.keyconfigs.addon
            km = kc.keymaps['3D View']

            kmis = []

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


        elif self.prefs_tabs == 'VHACD':
            for propName in self.vhacd_props:
                raw = layout.row()
                raw.prop(self, propName)

            row = layout.row()
            row.operator("wm.url_open", text="Open Link").url = "https://github.com/kmammou/v-hacd"
