import os
import platform
from pathlib import Path
from tempfile import gettempdir

import bpy
import rna_keymap_ui

from .naming_preset import COLLISION_preset
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..ui.properties_panels import OBJECT_MT_collision_presets
from ..ui.properties_panels import VIEW3D_PT_collission_material_panel
from ..ui.properties_panels import VIEW3D_PT_collission_panel
from ..ui.properties_panels import VIEW3D_PT_collission_visibility_panel
from ..ui.properties_panels import collider_presets_folder
from ..ui.properties_panels import label_multiline


def update_panel_category(self, context):
    '''Update panel tab for collider tools'''
    panelNames = [
        'VIEW3D_PT_collission_panel',
        'VIEW3D_PT_collission_visibility_panel',
        'VIEW3D_PT_collission_material_panel',
    ]

    panels = [
        VIEW3D_PT_collission_panel,
        VIEW3D_PT_collission_visibility_panel,
        VIEW3D_PT_collission_material_panel,

    ]
    for panel in panelNames:
        is_panel = hasattr(bpy.types, panel)

    for panel in panels:
        try:
            bpy.utils.unregister_class(panel)
        except:
            pass

        panel.bl_category = context.preferences.addons[__package__.split('.')[0]].preferences.collider_category
        bpy.utils.register_class(panel)
    return


def get_default_executable_path():
    '''Set the default exectuable path for the vhacd exe to the addon folder. '''
    path = Path(str(__file__))
    parent = path.parent.parent.absolute()

    vhacd_app_folder = "v-hacd_app"

    if platform.system() == 'Windows':
        OS_folder = 'Win'
        app_name = 'VHACD.exe'

    elif platform.system() == 'Darwin':
        OS_folder = 'OSX'
        app_name = 'VHACD'

    # Return empty string if the os is linux or unknown
    else:  # platform.system() == 'Linux':
        return ''

    collider_addon_directory = os.path.join(parent, vhacd_app_folder, OS_folder)

    if os.path.isdir(collider_addon_directory):
        executable_path = os.path.join(collider_addon_directory, app_name)
        if os.path.isfile(executable_path):
            return executable_path

    # if folder or file does not exist, return empty string
    return ''


class CollisionAddonPrefs(bpy.types.AddonPreferences):
    """Addon preferences for Collider Tools"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    bl_idname = __package__.split('.')[0]  ### __package__ works on multifile and __name__ not

    prefs_tabs: bpy.props.EnumProperty(
        name='Collision Settings',
        items=(('SETTINGS', "General", "General addon settings"),
               ('NAMING', "Presets",
                "Presets settings: Create, change and modify presets"),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon."),
               ('UI', "Ui", "Settings related to the Ui and display of the addon."),
               ('VHACD', "Auto Convex", "Settings related to Auto Convex generation.")),
        default='SETTINGS',
        description='Settings category:')

    ###################################################################
    # GENERAL

    collider_category: bpy.props.StringProperty(name="Category Tab",
                                                description="The category name used to organize the addon in the properties panel for all the addons",
                                                default='Collider Tools',
                                                update=update_panel_category)  # update = update_panel_position,
    # Collections
    use_col_collection: bpy.props.BoolProperty(name="Add Collider Collection",
                                               description="Link all collision objects to a specific Collection for collisions. It will create a collider collection with the given name if it doesn't already exist",
                                               default=True)

    col_collection_name: bpy.props.StringProperty(name='Collection Name',
                                                  description='Name of the collider collection newly created collisions are added to',
                                                  default='Collisions')

    ###################################################################
    # PRESETS

    naming_position: bpy.props.EnumProperty(
        name='Collider Naming',
        items=(('PREFIX', "Prefix", "Prefix"),
               ('SUFFIX', "Suffix", "Suffix")),
        default='PREFIX',
        description='Add custom naming as prefix or suffix'
    )

    replace_name: bpy.props.BoolProperty(name='Use Replace Name',
                                         description='Replace the name with a new one or use the name of the original object for the newly created collision name',
                                         default=False)

    basename: bpy.props.StringProperty(name="Replace Name", default="geo",
                                       description='The basename is used instead of the collider parent name when "Use Replace Name" is enabled.')

    separator: bpy.props.StringProperty(name="Separator", default="_",
                                        description="Separator character used to divide different suffixes (Empty field removes the separator from the naming)")

    collision_string_prefix: bpy.props.StringProperty(name="Collision Prefix", default="",
                                                      description='Simple string added to the beginning of the collider suffix/prefix.')

    collision_string_suffix: bpy.props.StringProperty(name="Collision Suffix", default="",
                                                      description='Simple string added to the end of the collider suffix/prefix.')

    # Collider Shapes
    box_shape: bpy.props.StringProperty(name="Box Collision", default="UBX",
                                        description='Naming used to define box colliders')
    sphere_shape: bpy.props.StringProperty(name="Sphere Collision", default="USP",
                                           description='Naming used to define sphere colliders')
    convex_shape: bpy.props.StringProperty(name="Convex Collision", default="UCX",
                                           description='Naming used to define convex colliders')
    mesh_shape: bpy.props.StringProperty(name="Mesh Collision", default="",
                                         description='Naming used to define triangle mesh colliders')

    # Collider Groups
    collider_groups_enabled: bpy.props.BoolProperty(name='Enable Collider Groups', description='', default=True)

    user_group_01_name: bpy.props.StringProperty(name="Display Name", default="Simple",
                                                 description='Naming of User Collider Group 01.')
    user_group_02_name: bpy.props.StringProperty(name="Display Name", default="Simple 2",
                                                 description='Naming of User Collider Group 02.')
    user_group_03_name: bpy.props.StringProperty(name="Display Name", default="Complex",
                                                 description='Naming of User Collider Group 03.')

    user_group_01: bpy.props.StringProperty(name="Pre/Suffix", default="",
                                            description='Naming of User Collider Group 01.')
    user_group_02: bpy.props.StringProperty(name="Pre/Suffix", default="",
                                            description='Naming of User Collider Group 02.')
    user_group_03: bpy.props.StringProperty(name="Pre/Suffix", default="Complex",
                                            description='Naming of User Collider Group 03.')

    physics_material_name: bpy.props.StringProperty(name='Default Physics Material',
                                                    default='MI_COL',
                                                    # type=bpy.types.Material,
                                                    # poll=scene_my_collision_material_poll,
                                                    description='Physical Materials are used in game enginges to define different responses of a physical object when interacting with other elements of the game world. They can be used to trigger different audio, VFX or gameplay events depending on the material. Collider Tools will create a simple semi transparent material called "COL_DEFAULT" if no material is assigned.')

    physics_material_filter: bpy.props.StringProperty(name='Physics Material Filter',
                                                      default="COL",
                                                      description='By default, the Physics Material input shows all materials of the blender scene. Use the filter to only display materials that contain the filter characters in their name. E.g.,  Using the filter "COL", all materials that do not have "COL" in their name will be hidden from the physics material selection.', )

    ###################################################################
    # UI

    # The object color for the bounding object
    user_group_01_color: bpy.props.FloatVectorProperty(name="User Group 1 Color",
                                                       description="Object color and alpha for User Collider Group 01",
                                                       default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
                                                       subtype='COLOR', size=4)

    # The object color for the bounding object
    user_group_02_color: bpy.props.FloatVectorProperty(name="User Group 2 Color",
                                                       description="Object color and alpha for User Collider Group 02",
                                                       default=(0.5, 1, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR',
                                                       size=4)

    # The object color for the bounding object
    user_group_03_color: bpy.props.FloatVectorProperty(name="User Group 3 Color",
                                                       description="Object color and alpha for User Collider Group 03.",
                                                       default=(1, 0.36, 0.36, 0.25), min=0.0, max=1.0, subtype='COLOR',
                                                       size=4)

    # Modal Fonts
    modal_color_default: bpy.props.FloatVectorProperty(name="Default",
                                                       description="Font Color in the 3D Viewport for settings that are reset every time the collision operator is called",
                                                       default=(1.0, 1.0, 1.0, 1), min=0.0, max=1.0,
                                                       subtype='COLOR', size=4)

    modal_color_title: bpy.props.FloatVectorProperty(name="Title",
                                                     description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_highlight: bpy.props.FloatVectorProperty(name="Active Highlight",
                                                         description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                         default=(0.0, 1.0, 1.0, 1.0), min=0.0, max=1.0,
                                                         subtype='COLOR', size=4)

    modal_color_modal: bpy.props.FloatVectorProperty(name="Modal",
                                                     description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_bool: bpy.props.FloatVectorProperty(name="Bool",
                                                    description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(1.0, 1.0, 0.75, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_color_enum: bpy.props.FloatVectorProperty(name="Enum",
                                                    description="Font Color in the 3D Viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(0.36, 0.75, 0.92, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_size: bpy.props.IntProperty(name='Font Size',
                                           description="Changes the font size in the 3D viewport when calling the modal collider_shapes to create different collision shapes",
                                           default=56)

    ###################################################################
    # VHACD
    # if platform.system() == 'Windows':
    default_executable_path: bpy.props.StringProperty(name='Default Executable',
                                                      description='Path to the V-Hacd executable distributed with this addon. (read-only)',
                                                      default= get_default_executable_path(),
                                                      subtype='FILE_PATH',
                                                      )


    executable_path: bpy.props.StringProperty(name='Overwrtie Executable',
                                              description='Specify a path to another V-hacd executable if you want to use a custom build',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(name='Temporary Data Path',
                                        description='Data path to store temporary files like meshes and log files sused by V-HACD to generate Auto Convex colliders',
                                        default=gettempdir(), maxlen=1024, subtype='DIR_PATH')

    # pre-process options
    remove_doubles: bpy.props.BoolProperty(name='Remove Doubles',
                                           description='Collapse overlapping vertices in generated mesh', default=True)

    # VHACD parameters
    vhacd_resolution: bpy.props.IntProperty(name='Voxel Resolution',
                                            description='Maximum number of voxels generated during the voxelization stage',
                                            default=100000, min=10000, max=64000000)
    vhacd_concavity: bpy.props.FloatProperty(name='Maximum Concavity', description='Maximum concavity', default=0.0015,
                                             min=0.0, max=1.0, precision=4)

    # Quality settings
    vhacd_planeDownsampling: bpy.props.IntProperty(name='Plane Downsampling',
                                                   description='Granularity of the search for the "best" clipping plane',
                                                   default=4, min=1, max=16)

    # Quality settings
    vhacd_convexhullDownsampling: bpy.props.IntProperty(name='Convex Hull Downsampling',
                                                        description='Precision of the convex-hull generation process during the clipping plane selection stage',
                                                        default=4, min=1, max=16)

    vhacd_alpha: bpy.props.FloatProperty(name='Alpha', description='Bias toward clipping along symmetry planes',
                                         default=0.05, min=0.0, max=1.0, precision=4)

    vhacd_beta: bpy.props.FloatProperty(name='Beta', description='Bias toward clipping along revolution axes',
                                        default=0.05,
                                        min=0.0, max=1.0, precision=4)

    vhacd_gamma: bpy.props.FloatProperty(name='Gamma', description='Maximum allowed concavity during the merge stage',
                                         default=0.00125, min=0.0, max=1.0, precision=5)

    vhacd_pca: bpy.props.BoolProperty(name='PCA',
                                      description='Enable/disable normalizing the mesh before applying the convex decomposition',
                                      default=False)

    vhacd_mode: bpy.props.EnumProperty(name='ACD Mode', description='Approximate convex decomposition mode',
                                       items=(('VOXEL', 'Voxel', 'Voxel ACD Mode'),
                                              ('TETRAHEDRON', 'Tetrahedron', 'Tetrahedron ACD Mode')), default='VOXEL')

    vhacd_minVolumePerCH: bpy.props.FloatProperty(name='Minimum Volume Per CH',
                                                  description='Minimum volume to add vertices to convex-hulls',
                                                  default=0.0001, min=0.0, max=0.01, precision=5)

    props = [
        "separator",
        "collision_string_prefix",
        "collision_string_suffix",
    ]

    props_shapes = [
        "box_shape",
        "sphere_shape",
        "convex_shape",
        "mesh_shape",
    ]

    props_collider_groups = [
        "collider_groups_enabled",
    ]

    props_collider_groups_identifier = [
        "user_group_01",
        "user_group_02",
        "user_group_03",
    ]

    props_collider_groups_name = [
        "user_group_01_name",
        "user_group_02_name",
        "user_group_03_name",
    ]

    props_physics_materials = [
        "physics_material_name",
        "physics_material_filter",
    ]

    col_props = [
        "use_col_collection",
        "col_collection_name",
    ]

    ui_col_colors = [
        'user_group_01_color',
        'user_group_02_color',
        'user_group_03_color',
    ]

    ui_props = [
        "modal_font_size",
        "modal_color_title",
        "modal_color_highlight",
        "modal_color_modal",
        "modal_color_bool",
        "modal_color_default",
        "modal_color_enum",
    ]

    vhacd_props_config = [
        "vhacd_resolution",
        "vhacd_concavity",
        "vhacd_planeDownsampling",
        "vhacd_convexhullDownsampling",
        "vhacd_alpha",
        "vhacd_beta",
        "vhacd_gamma",
        "vhacd_pca",
        "vhacd_mode",
        "vhacd_minVolumePerCH",
    ]

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':

            row = layout.row()
            row.label(text='Collections')

            for propName in self.col_props:
                row = layout.row()
                row.prop(self, propName)

        if self.prefs_tabs == 'NAMING':
            box = layout.box()

            row = box.row(align=True)
            row.label(text="Presets")
            row.menu(OBJECT_MT_collision_presets.__name__, text=OBJECT_MT_collision_presets.bl_label)
            row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
            row.operator(COLLISION_preset.bl_idname, text="", icon='REMOVE').remove_active = True
            row.operator("wm.url_open", text="",
                         icon='HELP').url = "https://weisl.github.io/collider-tools_import_engines/"
            if platform.system() == 'Windows':
                op = row.operator("explorer.open_in_explorer", text="", icon='FILE_FOLDER')
                op.dirpath = collider_presets_folder()

            boxname = box.box()
            row = box.row()
            row.prop(self, "naming_position", expand=True)

            row = boxname.row()
            if self.naming_position == 'PREFIX':
                row.label(text="Name = Collision Prefix + Shape + Group + Collision Suffix + Basename + Numbering")
            else:  # self.naming_position == 'SUFFIX':
                row.label(text="Name = Basename + Collision Prefix + Shape + Group + Collision Suffix + Numbering")

            row = boxname.row()
            row.label(text="E.g. " + OBJECT_OT_add_bounding_object.class_collider_name(self.box_shape,
                                                                                       'USER_01',
                                                                                       basename='Suzanne'))

            row = box.row()
            row.prop(self, "replace_name")

            row = box.row()

            if not self.replace_name:
                row.enabled = False
            row.prop(self, "basename")

            for propName in self.props:
                row = box.row()
                row.prop(self, propName)

            box2 = layout.box()
            box2.label(text="Shape")
            for propName in self.props_shapes:
                row = box2.row()
                row.prop(self, propName)

            box = layout.box()
            box.label(text="Collider Groups")
            for propName in self.props_collider_groups:
                row = box.row()
                row.prop(self, propName)

            count = 1
            for prop_01, prop_02 in zip(self.props_collider_groups_name, self.props_collider_groups_identifier):
                split = box.split(align=True, factor=0.1)
                split.label(text="Group_" + str(count) + ":")

                split = split.split(align=True, factor=0.5)
                split.prop(self, prop_01)
                split.prop(self, prop_02)
                count += 1

            box = layout.box()
            box.label(text="Physics Materials")
            for propName in self.props_physics_materials:
                row = box.row()
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
            kmis.append(get_hotkey_entry_item(km, 'wm.call_panel', 'VIEW3D_PT_collission_visibility_panel'))
            kmis.append(get_hotkey_entry_item(km, 'wm.call_panel', 'VIEW3D_PT_collission_material_panel'))

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
            texts = []

            text = "Auto convex is only supported for Windows at this moment."
            texts.append(text)

            if platform.system() != 'Windows':
                for text in texts:
                    label_multiline(
                        context=context,
                        text=text,
                        parent=layout
                    )
                return

            text = "The auto convex collision generation requires the V-hacd library to work. "
            texts.append(text)

            box = layout.box()
            row = box.row()
            row.label(text="Information about the executable: V-Hacd Github")
            row.operator("wm.url_open", text="", icon='URL').url = "https://github.com/kmammou/v-hacd"

            for text in texts:
                label_multiline(
                    context=context,
                    text=text,
                    parent=box
                )

            row = layout.row()
            row.enabled = False
            row.prop(self, 'default_executable_path')

            row = layout.row()
            row.prop(self, 'executable_path')

            row = layout.row()
            if self.data_path:
                row.prop(self, "data_path")
            else:  # temp folder is missing
                box = layout.box()
                text = "The auto convex collider requires temporary files to be stored on your pc to allow for the communication of Blender and the V-hacd executable. You can change the directory for storing the temporary data from here."
                label_multiline(
                    context=context,
                    text=text,
                    parent=box
                )
                row.prop(self, "data_path", icon="ERROR")

            if self.executable_path or self.default_executable_path:

                layout.separator()

                box = layout.box()
                row = box.row()
                row.label(text="Generation Settings")
                row = box.row()
                row.label(text="Parameter Information")

                row.operator("wm.url_open",
                             text="Github: Kmammou V-hacd").url = "https://github.com/kmammou/v-hacd"
                for propName in self.vhacd_props_config:
                    row = box.row()
                    row.prop(self, propName)
