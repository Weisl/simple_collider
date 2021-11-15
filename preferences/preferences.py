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

    prefs_tabs: bpy.props.EnumProperty(
        name='Collision Settings',
        items=(('NAMING', "Naming", "NAMING"), ('UI', "UI", "UI"), ('VHACD', "V-HACD", "VHACD")),
        default='NAMING',
        description='Tabs to toggle different addon settings')

    naming_position: bpy.props.EnumProperty(
        name='Collider Naming',
        items=(('PREFIX', "Prefix", "Prefix"), ('SUFFIX', "Suffix", "Suffix")),
        default='SUFFIX',
        description='Add custom naming as prefix or suffix'
    )

    separator: bpy.props.StringProperty(name="Separator ", default="_", description="Separator character used to divide different suffixes (Empty field removes the separator from the naming)")
    colPreSuffix: bpy.props.StringProperty(name="Collision ", default="COL",  description='Simple string (text) added to the name of the collider')
    optionalSuffix: bpy.props.StringProperty(name="Additional Suffix (optional)", default="",  description='Additional string (text) added to the name of the collider for custom purpose')
    basename: bpy.props.StringProperty(name="Collider Base Name", default="geo",  description='')

    # Collider Complexity
    colSimpleComplex: bpy.props.StringProperty(name="SIMPLE-COMPLEX Collisions", default="SIMPLE_COMPLEX", description='Naming used for simple-complex collisions')
    colSimple: bpy.props.StringProperty(name="Simple Collisions", default="SIMPLE", description='Naming used for simple collisions')
    colComplex: bpy.props.StringProperty(name="Complex Collisions", default="COMPLEX", description='Naming used for complex collisions')

    # Non collider
    colSuffix: bpy.props.StringProperty(name="Non Collision", default="BOUNDING",  description='Simple string (text) added to the name when not creating a collider')

    # Collider Shapes
    boxColSuffix: bpy.props.StringProperty(name="Box Collision", default="BOX", description='Naming used to define box collisions')
    convexColSuffix: bpy.props.StringProperty(name="Convex Collision", default="CONVEX", description='Naming used to define convex collisions')
    sphereColSuffix: bpy.props.StringProperty(name="Sphere Collision", default="SPHERE", description='Naming used to define sphere collisions')
    meshColSuffix: bpy.props.StringProperty(name="Mesh Collision", default="MESH", description='Naming used to define triangle mesh collisions')

    use_col_Complexity: bpy.props.BoolProperty(
        name = 'Use Complexity',
        description = 'Use Complexity',
        default = True
    )

    # The object color for the bounding object
    my_color_simple_complex : bpy.props.FloatVectorProperty(name="Simple Complex Color", description="Object color and alpha for simple-complex collisions", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    # The object color for the bounding object
    my_color_simple : bpy.props.FloatVectorProperty(name="Simple Color", description="Object color and alpha for simple collisions", default=(0.5, 1, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    # The object color for the bounding object
    my_color_complex : bpy.props.FloatVectorProperty(name="Complex Color", description="Object color and alpha for complex collisions", default=(1, 0.36, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    #Modal Fonts
    modal_font_color: bpy.props.FloatVectorProperty(name="Font Operator", description="Font Color in the 3D Viewport for settings that are reset every time the collision operator is called",
                                                    default=(0.75, 0.75, 0.75, 0.5), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)
    modal_font_color_scene: bpy.props.FloatVectorProperty(name="Font Permanent", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(1, 1, 1, 0.5), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_color_title: bpy.props.FloatVectorProperty(name="Title Font Color", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(0.5, 0.8, 0.5, 1), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)


    modal_font_size: bpy.props.IntProperty(name='Font Size', description="Changes the font size in the 3D viewport when calling the modal operators to create different collision shapes", default=72)

    use_col_collection: bpy.props.BoolProperty(name='Add Collision Collection',
                                               description='Link all collision objects to a specific Collection for collisions',default = True)
    use_parent_name: bpy.props.BoolProperty(name='Keep Name', description='Keep the name of the original object for the newly created collision object',default = True)
    col_collection_name: bpy.props.StringProperty(name='Collection Name',description='Name of the collection newly created collisions get added to',default='Col')

    #### VHACD ####

    executable_path: bpy.props.StringProperty(name='VHACD exe',
                                              description='Path to VHACD executable',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(name='Data Path',description='Data path to store V-HACD meshes and logs',default=gettempdir(),maxlen=1024,subtype='DIR_PATH')
    name_template: bpy.props.StringProperty(name='Name Template',
                                            description='Name template used for generated hulls.\n? = original mesh name\n# = hull id',default='?_hull_#',)
    # pre-process options
    remove_doubles: bpy.props.BoolProperty(name='Remove Doubles',description='Collapse overlapping vertices in generated mesh',default=True)
    apply_transforms: bpy.props.EnumProperty(name='Apply',description='Apply Transformations to generated mesh',
                                             items=(('LRS', 'Location + Rotation + Scale', 'Apply location, rotation and scale'),
                                                    ('RS', 'Rotation + Scale', 'Apply rotation and scale'),
                                                    ('S', 'Scale', 'Apply scale only'),
                                                    ('NONE', 'None', 'Do not apply transformations'),
                                                    ),default='NONE')

    # VHACD parameters
    resolution: bpy.props.IntProperty(name='Voxel Resolution',
                            description='Maximum number of voxels generated during the voxelization stage',
                            default=100000, min=10000, max=64000000)
    concavity: bpy.props.FloatProperty(name='Maximum Concavity',description='Maximum concavity',default=0.0015,min=0.0,max=1.0,precision=4)

    # Quality settings
    planeDownsampling: bpy.props.IntProperty(name='Plane Downsampling',description='Granularity of the search for the "best" clipping plane',default=4,min=1,max=16)

    # Quality settings
    convexhullDownsampling: bpy.props.IntProperty(name='Convex Hull Downsampling',description='Precision of the convex-hull generation process during the clipping plane selection stage',
                                                  default=4,min=1,max=16)

    alpha: bpy.props.FloatProperty(name='Alpha',description='Bias toward clipping along symmetry planes',
                                   default=0.05,min=0.0,max=1.0,precision=4)

    beta: bpy.props.FloatProperty(name='Beta',description='Bias toward clipping along revolution axes',default=0.05,min=0.0,max=1.0,precision=4)

    gamma: bpy.props.FloatProperty(name='Gamma',description='Maximum allowed concavity during the merge stage',default=0.00125,min=0.0,max=1.0,precision=5)

    pca: bpy.props.BoolProperty(name='PCA',description='Enable/disable normalizing the mesh before applying the convex decomposition',default=False)

    mode: bpy.props.EnumProperty(name='ACD Mode',description='Approximate convex decomposition mode',
                       items=(('VOXEL', 'Voxel', 'Voxel ACD Mode'),('TETRAHEDRON', 'Tetrahedron', 'Tetrahedron ACD Mode')),default='VOXEL')

    minVolumePerCH: bpy.props.FloatProperty(name='Minimum Volume Per CH',description='Minimum volume to add vertices to convex-hulls',
                                            default=0.0001, min=0.0, max=0.01, precision=5)

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
        "use_col_collection",
        "col_collection_name",
    ]

    ui_props = [
        "modal_font_color",
        "modal_font_color_scene",
        "modal_font_size",
    ]

    vhacd_props = [
        "executable_path",
        "data_path",
        "name_template",
    ]

    vhacd_props_config = [
        "resolution",
        "concavity",
        "resolution",
        "concavity",
        "planeDownsampling",
        "convexhullDownsampling",
        "alpha",
        "beta",
        "gamma",
        "pca",
        "mode",
        "minVolumePerCH",
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
            row.prop(self, "naming_position", expand=True)

            for propName in self.props:
                row = layout.row()
                row.prop(self, propName)


        elif self.prefs_tabs == 'UI':

            box = layout.box()
            col = box.column()
            col.label(text="keymap")

            layout.separator()
            row = layout.row()
            row.prop(self, 'my_color_all')
            row = layout.row()
            row.prop(self, 'my_color_simple')
            row = layout.row()
            row.prop(self, 'my_color_complex')

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

            for propName in self.ui_props:
                row = layout.row()
                row.prop(self, propName)



        elif self.prefs_tabs == 'VHACD':
            for propName in self.vhacd_props:
                raw = layout.row()
                raw.prop(self, propName)
            row = layout.row()
            row.operator("wm.url_open", text="Open Link").url = "https://github.com/kmammou/v-hacd"

            layout.separator()

            box = layout.box()
            for propName in self.vhacd_props_config:
                raw = box.row()
                raw.prop(self, propName)
