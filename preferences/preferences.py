import bpy
import rna_keymap_ui
import bpy

from tempfile import gettempdir
from .naming_preset import COLLISION_preset
from .naming_preset import OBJECT_MT_collision_presets
from ..ui.properties_panels import VIEW3D_PT_collission_panel
from ..ui.properties_panels import label_multiline
from ..operators.add_bounding_primitive import create_name_number



def update_panel_category(self, context):
    is_panel = hasattr(bpy.types, 'VIEW3D_PT_collission_panel')

    if is_panel:
        try:
            bpy.utils.unregister_class(VIEW3D_PT_collission_panel)
        except:
            pass

    VIEW3D_PT_collission_panel.bl_category = context.preferences.addons[__package__.split('.')[0]].preferences.collider_category
    bpy.utils.register_class(VIEW3D_PT_collission_panel)
    return


class CollisionAddonPrefs(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    bl_idname = __package__.split('.')[0]  ### __package__ works on multifile and __name__ not

    prefs_tabs: bpy.props.EnumProperty(
        name='Collision Settings',
        items=(('SETTINGS', "Settings", "settings"),('NAMING', "Naming", "naming"), ('KEYMAP', "Keymap", "keymap"), ('UI', "Ui", "ui"), ('VHACD', "Auto Convex", "auto_convex")),
        default='SETTINGS',
        description='Tabs to toggle different addon settings')


    collider_category: bpy.props.StringProperty(name="Category Name",
                                      description="Category name used to organize the addon in the properties panel for all the addons.",
                                      default='Collider Tools', update=update_panel_category)  # update = update_panel_position,

    #Naming
    naming_position: bpy.props.EnumProperty(
        name='Collider Naming',
        items=(('PREFIX', "Prefix", "Prefix"), ('SUFFIX', "Suffix", "Suffix")),
        default='PREFIX',
        description='Add custom naming as prefix or suffix'
    )
    separator: bpy.props.StringProperty(name="Separator", default="_", description="Separator character used to divide different suffixes (Empty field removes the separator from the naming)")

    basename: bpy.props.StringProperty(name="Replace Basename", default="geo",  description='')
    replace_name: bpy.props.BoolProperty(name='Use Replace Name', description='Replace the name with a new one or use the name of the original object for the newly created collision name', default = False)

    colPreSuffix: bpy.props.StringProperty(name="Collision Pre", default="",  description='Simple string (text) added to the name of the collider')
    optionalSuffix: bpy.props.StringProperty(name="Collision Post", default="",  description='Additional string (text) added to the name of the collider for custom purpose')


    # Collider Complexity
    IgnoreShapeForComplex:  bpy.props.BoolProperty(name='UE: Complex Naming', description='Ignore Shape names for Complex Collisions to work for the Unreal Engine', default=False)

    colSimpleComplex: bpy.props.StringProperty(name="Simple & Complex", default="", description='Naming used for simple-complex collisions')
    colSimple: bpy.props.StringProperty(name="Simple", default="", description='Naming used for simple collisions')
    colComplex: bpy.props.StringProperty(name="Complex", default="Complex", description='Naming used for complex collisions')

    # Collider Shapes
    boxColSuffix: bpy.props.StringProperty(name="Box Collision", default="UBX", description='Naming used to define box collisions')
    convexColSuffix: bpy.props.StringProperty(name="Convex Collision", default="UCX", description='Naming used to define convex collisions')
    sphereColSuffix: bpy.props.StringProperty(name="Sphere Collision", default="USP", description='Naming used to define sphere collisions')
    meshColSuffix: bpy.props.StringProperty(name="Mesh Collision", default="Mesh", description='Naming used to define triangle mesh collisions')

    #COLORS
    # The object color for the bounding object
    my_color_simple_complex : bpy.props.FloatVectorProperty(name="Simple Complex Color", description="Object color and alpha for simple-complex collisions", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    # The object color for the bounding object
    my_color_simple : bpy.props.FloatVectorProperty(name="Simple Color", description="Object color and alpha for simple collisions", default=(0.5, 1, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    # The object color for the bounding object
    my_color_complex : bpy.props.FloatVectorProperty(name="Complex Color", description="Object color and alpha for complex collisions", default=(1, 0.36, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR', size=4)

    #Modal Fonts
    modal_color_default: bpy.props.FloatVectorProperty(name="Default", description="Font Color in the 3D Viewport for settings that are reset every time the collision operator is called",
                                                       default=(1.0, 1.0, 1.0, 1), min=0.0, max=1.0,
                                                       subtype='COLOR', size=4)

    modal_color_title: bpy.props.FloatVectorProperty(name="Title", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)
    modal_color_highlight: bpy.props.FloatVectorProperty(name="Active Highlight", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                         default=(0.0, 1.0, 1.0, 1.0), min=0.0, max=1.0,
                                                         subtype='COLOR', size=4)

    modal_color_modal: bpy.props.FloatVectorProperty(name="Modal", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_bool: bpy.props.FloatVectorProperty(name="Bool", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.75, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)


    modal_color_enum: bpy.props.FloatVectorProperty(name="Enum", description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(0.36, 0.75, 0.92, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_size: bpy.props.IntProperty(name='Font Size', description="Changes the font size in the 3D viewport when calling the modal operators to create different collision shapes", default=56)

    padding_bottom: bpy.props.IntProperty(name='Padding Bottom', description="The text padding in px. The padding defines the distance between the viewport bottom and the start of the modal operator text.", default=100)

    ## Collections
    use_col_collection: bpy.props.BoolProperty(name='Add Collision Collection',
                                               description='Link all collision objects to a specific Collection for collisions',default = True)
    col_collection_name: bpy.props.StringProperty(name='Collection Name',description='Name of the collection newly created collisions get added to',default='Collisions')

    #### VHACD ####

    executable_path: bpy.props.StringProperty(name='VHACD exe',
                                              description='Path to VHACD executable',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(name='Data Path',description='Data path to store V-HACD meshes and logs',default=gettempdir(),maxlen=1024,subtype='DIR_PATH')

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
        "separator",
        "colPreSuffix",
        "optionalSuffix",
    ]

    props_shapes = [
        "meshColSuffix",
        "convexColSuffix",
        "boxColSuffix",
        "sphereColSuffix",
    ]

    props_complexity = [
        "IgnoreShapeForComplex",
        "colSimple",
        "colComplex",
        "colSimpleComplex",
    ]

    col_props = [
        "use_col_collection",
        "col_collection_name",
    ]

    ui_col_colors = [
        'my_color_simple_complex',
        'my_color_simple',
        'my_color_complex',
    ]

    ui_props = [
        "modal_font_size",
        # "padding_bottom",
        "modal_color_title",
        "modal_color_highlight",
        "modal_color_modal",
        "modal_color_bool",
        "modal_color_default",
        "modal_color_enum",
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

    def collider_name(self, basename = 'Basename'):
        separator = self.separator

        if self.replace_name:
            name = self.basename
        else:
            name = basename

        pre_suffix_componetns = [
            self.colPreSuffix,
            self.boxColSuffix,
            self.colSimpleComplex,
            self.optionalSuffix,
        ]

        name_pre_suffix = ''
        if self.naming_position == 'SUFFIX':
            for comp in pre_suffix_componetns:
                if comp:
                    name_pre_suffix = name_pre_suffix + separator + comp
            new_name = name + name_pre_suffix

        else: #self.naming_position == 'PREFIX'
            for comp in pre_suffix_componetns:
                if comp:
                    name_pre_suffix = name_pre_suffix + comp + separator
            new_name = name_pre_suffix + name

        return create_name_number(new_name, nr=1)

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':

            row = layout.row()
            row.label(text='Collection Settings')

            for propName in self.col_props:
                row = layout.row()
                row.prop(self, propName)


        if self.prefs_tabs == 'NAMING':
            row = layout.row(align=True)

            box = layout.box()

            row = box.row(align=True)
            row.label(text="Naming Settings")

            row = box.row(align=True)
            row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)
            row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
            row.operator(COLLISION_preset.bl_idname, text="", icon='REMOVE').remove_active = True




            row = box.row(align=True)
            row.label(text="Download game engine naming presets")

            row = box.row(align=True)
            row.label(text="Download Presets:")
            row.operator("wm.url_open",
                         text="UE").url = "https://weisl.github.io//files//UE.py"

            row.operator("wm.url_open",
                         text="Unity").url = "https://weisl.github.io//files//default.py"

            row = box.row(align=True)
            row.label(text="How to install Presets")
            row.operator("wm.url_open",
                         text="Documentation").url = "https://weisl.github.io/collider-tools_import_engines/"


            boxname = box.box()
            row = box.row()
            row.prop(self, "naming_position", expand=True)

            row = boxname.row()
            if self.naming_position == 'PREFIX':
                row.label(text="Name = Collision Pre + Shape + Complexity + Collision Post + Basename + Numbering")
            else:
                row.label(text="Name = Basename + Collision Pre + Shape + Complexity + Collision Post + Numbering")

            row = boxname.row()
            row.label(text="E.g. " + self.collider_name(basename='Suzanne'))

            row = box.row()
            row.prop(self, "replace_name")

            row = box.row()
            if self.replace_name:
                row.prop(self, "basename")
            else:
                row.prop(self, "basename", icon="ERROR")

            for propName in self.props:
                row = box.row()
                row.prop(self, propName)

            box2 = layout.box()
            box2.label(text="Shape")
            for propName in self.props_shapes:
                row = box2.row()
                row.prop(self, propName)

            box3 = layout.box()
            box3.label(text="Complexity")
            for propName in self.props_complexity:
                row = box3.row()
                row.prop(self, propName)


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

        elif self.prefs_tabs == 'UI':

            row = layout.row()
            row.prop(self, "collider_category", expand=True)

            layout.separator()
            row = layout.row()
            row.label(text="3D Viewport Colors")

            for propName in self.ui_col_colors:
                row = layout.row()
                row.prop(self, propName)

            row = layout.row()
            row.label(text="UI Settings")

            for propName in self.ui_props:
                row = layout.row()
                row.prop(self, propName)


        elif self.prefs_tabs == 'VHACD':

            text = "The auto convex collision generation requires the V-hacd library to work."
            label_multiline(
                context=context,
                text=text,
                parent=layout
            )

            texts=[]
            if not self.executable_path or not self.data_path:
                texts.append("1. Download the V-hacd executable from the link below (Download V-hacd). If you encounter any issues, try using the Chrome browser. Edge requires you to confirm the download for security reasons. (optional) Copy the downloaded executable to another directory on your hard drive.")
                texts.append("2. Press the small folder icon of the 'V-hacd exe' input to open a file browser. Select the V-hacd.exe you have just downloaded before and confirm with 'Accept'.")
                texts.append("3. The auto convex collider requires temporary files to be stored on your pc to allow for the communication of Blender and the V-hacd executable. You can change the directory for storing the temporary data from here.")


                box = layout.box()
                for text in texts:
                    label_multiline(
                        context=context,
                        text=text,
                        parent=box
                    )

            row = layout.row(align = True)
            row.label(text="1. Download V-HACD")
            row.operator("wm.url_open", text="Win").url = "https://github.com/kmammou/v-hacd/raw/master/app/TestVHACD.exe"
            # row.operator("wm.url_open", text="OSX (untested)").url = "https://github.com/kmammou/v-hacd/raw/master/bin-no-ocl/osx/testVHACD"

            row = layout.row()
            if self.executable_path:
                row.prop(self, 'executable_path', text='2. V-hacd .exe path')
            else:
                row.prop(self, 'executable_path', text='2. V-hacd .exe path', icon="ERROR")

            row = layout.row()
            if self.data_path:
                row.prop(self, "data_path", text = "3. Temporary Data Path")
            else:
                row.prop(self, "data_path", text="3. Temporary Data Path", icon="ERROR")


            box = layout.box()
            row = box.row()
            row.label(text="Information about the executable: V-Hacd Github")
            row = box.row()
            row.operator("wm.url_open", text="Github: Kmammou V-hacd").url = "https://github.com/kmammou/v-hacd"

            if self.executable_path:

                layout.separator()

                box = layout.box()
                row = box.row()
                row.label(text="Generation Settings")
                row = box.row()
                row.label(text="Parameter Information")

                if self.executable_path:
                    row.operator("wm.url_open", text="Github: Kmammou V-hacd").url = "https://github.com/kmammou/v-hacd"
                    for propName in self.vhacd_props_config:
                        row = box.row()
                        row.prop(self, propName)
                else:
                    row = box.row()
                    row.label(text="Install V-HACD", icon="ERROR")

