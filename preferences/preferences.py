import bpy
import os
import platform
from bpy.app.handlers import persistent
from pathlib import Path
from tempfile import gettempdir

from .keymap import keymaps_items_dict
from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..groups.user_groups import set_default_group_values
from ..presets.naming_preset import COLLISION_preset
from ..presets.preset_operator import SetSimpleColliderPreferencesOperator
from ..presets.presets_data import presets
from ..pyshics_materials.material_functions import set_default_active_mat
from ..ui.properties_panels import OBJECT_MT_collision_presets
from ..ui.properties_panels import VIEW3D_PT_collision_material_panel
from ..ui.properties_panels import VIEW3D_PT_collision_panel
from ..ui.properties_panels import VIEW3D_PT_collision_settings_panel
from ..ui.properties_panels import VIEW3D_PT_collision_visibility_panel
from ..ui.properties_panels import label_multiline

collection_colors = [
    ("NONE", "White", "Default collection color", "OUTLINER_COLLECTION", 0),
    ("COLOR_01", "Red", "Red collection color", "COLLECTION_COLOR_01", 1),
    ("COLOR_02", "Orange", "Orange collection color", "COLLECTION_COLOR_02", 2),
    ("COLOR_03", "Yellow", "Yellow collection color", "COLLECTION_COLOR_03", 3),
    ("COLOR_04", "Green", "Green collection color", "COLLECTION_COLOR_04", 4),
    ("COLOR_05", "Blue", "Blue collection color", "COLLECTION_COLOR_05", 5),
    ("COLOR_06", "Violet", "Violet collection color", "COLLECTION_COLOR_06", 6),
    ("COLOR_07", "Pink", "Pink collection color", "COLLECTION_COLOR_07", 7),
    ("COLOR_08", "Brown", "Brown collection color", "COLLECTION_COLOR_08", 8),
]


def setDefaultTemp():
    """
    Set the default temporary directory for the simple collider addon.

    This function creates a new directory in the system's temporary directory
    for storing temporary files used by the simple collider addon.

    Returns:
        File path to the temporary directory
    """
    system_temp_dir = gettempdir()
    path = os.path.join(system_temp_dir, "simple_collider")

    # Check whether the specified path exists or not
    if not os.path.exists(path):
        # Create a new directory because it does not exist
        os.makedirs(path)

    return path


def update_panel_category(self, context):
    """Update panel tab for collider tools"""
    panels = [
        VIEW3D_PT_collision_panel,
        VIEW3D_PT_collision_settings_panel,
        VIEW3D_PT_collision_visibility_panel,
        VIEW3D_PT_collision_material_panel,
    ]

    for panel in panels:
        try:
            bpy.utils.unregister_class(panel)
        except:
            pass

        panel.bl_category = context.preferences.addons[base_package].preferences.collider_category
        bpy.utils.register_class(panel)
    return


def get_default_executable_path():
    """Set the default executable path for the vhacd executable to the addon folder. """
    path = Path(str(__file__))
    parent = path.parent.parent.absolute()

    vhacd_app_folder = "v-hacd_app"

    if platform.system() not in ['Windows', 'Linux']:
        return ''

    OS_folder = ''
    app_name = ''

    if platform.system() == 'Windows':
        OS_folder = 'Win'
        app_name = 'VHACD-4_1.exe'
    elif platform.system() == 'Linux':
        OS_folder = 'Linux'
        app_name = 'VHACD'

    collider_addon_directory = os.path.join(
        parent, vhacd_app_folder, OS_folder)

    if os.path.isdir(collider_addon_directory):
        executable_path = os.path.join(collider_addon_directory, app_name)
        if os.path.isfile(executable_path):
            return executable_path

    # if folder or file does not exist, return empty string
    return ''


def update_keymap(self, context, keymap_name):
    wm = context.window_manager
    addon_km = wm.keyconfigs.addon.keymaps.get("Window") # Using Window instead of 3D View to fix issue of keymap not working on Linux
    if not addon_km:
        return

    from .keymap import keymaps_items_dict
    item = keymaps_items_dict[keymap_name]
    name = item["name"]
    idname = item["idname"]
    operator = item["operator"]

    # Get current values from preferences
    key_type = getattr(self, f"{name}_type").upper()
    ctrl = getattr(self, f"{name}_ctrl")
    shift = getattr(self, f"{name}_shift")
    alt = getattr(self, f"{name}_alt")
    active = getattr(self, f"{name}_active")  # Get the active state from preferences

    # Remove existing keymap items for this operator
    for kmi in addon_km.keymap_items[:]:
        if kmi.idname == idname and hasattr(kmi.properties, 'name') and kmi.properties.name == operator:
            addon_km.keymap_items.remove(kmi)

    # Add new keymap item if type is not 'NONE'
    if key_type != 'NONE':
        kmi = addon_km.keymap_items.new(
            idname=idname,
            type=key_type,
            value='PRESS',
            ctrl=ctrl,
            shift=shift,
            alt=alt,
        )
        kmi.properties.name = operator
        kmi.active = active  # Set the active state from preferences
    else:
        # If type is 'NONE', ensure no keymap item exists
        pass

    wm.keyconfigs.update()  # Refresh keymaps to apply changes

class CollisionAddonPrefs(bpy.types.AddonPreferences):
    """Addon preferences for Simple Collider"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    # __package__ works on multi file and __name__ not
    bl_idname = base_package
    bl_options = {'REGISTER'}

    prefs_tabs: bpy.props.EnumProperty(
        name='Collider Settings',
        items=(('SETTINGS', "General", "General addon settings"),
               ('NAMING', "Presets", "Presets settings: Create, change and modify presets"),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon."),
               ('UI', "Ui", "Settings related to the Ui and display of the addon."),
               ('VHACD', "Auto Convex", "Settings related to Auto Convex generation."),
               ('SUPPORT', "Support", "Get support and help with the addon and help improve it"),
               ),
        default='SETTINGS',
        description='Settings category:')

    ###################################################################

    collider_category: bpy.props.StringProperty(name="Category Tab",
                                                description="The category name used to organize the addon in the properties panel for all the addons",
                                                default='Simple Collider',
                                                update=update_panel_category)  # update = update_panel_position,

    ############################
    #Generation
    fix_parent_inverse_mtrx: bpy.props.BoolProperty(name="Fix Parent Inverse Matrix",
                                          description="Fix the parent inverse matrix of the collider if the collider is parented to another object. This will ensure that the collider is correctly positioned relative to its parent.",
                                          default=True)

    # GENERAL
    # Parent to base
    use_parent_to: bpy.props.BoolProperty(name="Parent Colliders to Base Objects",
                                          description="Parent the newly generated collider to the base mesh it was created from.",
                                          default=True)

    # Modifiers
    keep_modifier_defaults: bpy.props.BoolProperty(name="Keep Collider Modifiers with default values",
                                                   description="Keep the collider modifiers using the default values and don't manipulate the geometry.",
                                                   default=True)

    # Collections
    use_col_collection: bpy.props.BoolProperty(name="Add Collider Collection",
                                               description="Link all collision objects to a specific Collection for collisions. It will create a collider collection with the given name if it doesn't already exist",
                                               default=True)

    col_collection_name: bpy.props.StringProperty(name='Collection Name',
                                                  description='Name of the collider collection newly created collisions are added to',
                                                  default='Colliders')

    col_collection_color: bpy.props.EnumProperty(name='Collection Color',
                                                 items=collection_colors,
                                                 description='Choose the color for the collider collections.',
                                                 default='COLOR_05',
                                                 )

    col_tmp_collection_color: bpy.props.EnumProperty(name='Temp Collection Color',
                                                     items=collection_colors,
                                                     description='Choose the color for the collider collections.',
                                                     default='COLOR_03',
                                                     )

    ###################################################################
    # KEYMAP

    collision_pie_type: bpy.props.StringProperty(
        name="Collider Pie Menu",
        default=keymaps_items_dict["Collider Pie Menu"]["type"],
        update=lambda self, context: update_keymap(self, context, "Collider Pie Menu")
    )

    collision_pie_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Collider Pie Menu"]["ctrl"],
        update=lambda self, context: update_keymap(self, context, "Collider Pie Menu")
    )
    collision_pie_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Collider Pie Menu"]["shift"],
        update=lambda self, context: update_keymap(self, context, "Collider Pie Menu")
    )
    collision_pie_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Collider Pie Menu"]["alt"],
        update=lambda self, context: update_keymap(self, context, "Collider Pie Menu")
    )
    collision_pie_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Collider Pie Menu"]["active"],
        update=lambda self, context: update_keymap(self, context, "Collider Pie Menu")
    )

    collision_visibility_type: bpy.props.StringProperty(
        name="Visibility Menu",
        default=keymaps_items_dict["Visibility Menu"]["type"],
        update=lambda self, context: update_keymap(self, context, "Visibility Menu")
    )
    collision_visibility_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Visibility Menu"]["ctrl"],
        update=lambda self, context: update_keymap(self, context, "Visibility Menu")
    )
    collision_visibility_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Visibility Menu"]["shift"],
        update=lambda self, context: update_keymap(self, context, "Visibility Menu")
    )
    collision_visibility_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Visibility Menu"]["alt"],
        update=lambda self, context: update_keymap(self, context, "Visibility Menu")
    )
    collision_visibility_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Visibility Menu"]["active"],
        update=lambda self, context: update_keymap(self, context, "Visibility Menu")
    )

    collision_material_type: bpy.props.StringProperty(
        name="Material Menu",
        default=keymaps_items_dict["Material Menu"]["type"],
        update=lambda self, context: update_keymap(self, context, "Material Menu")
    )
    collision_material_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Material Menu"]["ctrl"],
        update=lambda self, context: update_keymap(self, context, "Material Menu")
    )
    collision_material_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Material Menu"]["shift"],
        update=lambda self, context: update_keymap(self, context, "Material Menu")
    )
    collision_material_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Material Menu"]["alt"],
        update=lambda self, context: update_keymap(self, context, "Material Menu")
    )
    collision_material_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Material Menu"]["active"],
        update=lambda self, context: update_keymap(self, context, "Material Menu")
    )

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

    obj_basename: bpy.props.StringProperty(name="Replace Name", default="geo",
                                           description='The basename is used instead of the collider parent name when "Use Replace Name" is enabled')

    separator: bpy.props.StringProperty(name="Separator", default="_",
                                        description="Separator character used to divide different suffixes (Empty field removes the separator from the naming)")

    collision_string_prefix: bpy.props.StringProperty(name="Collider Prefix", default="",
                                                      description='Simple string added to the beginning of the collider suffix/prefix')

    collision_string_suffix: bpy.props.StringProperty(name="Collider Suffix", default="",
                                                      description='Simple string added to the end of the collider suffix/prefix')

    collision_digits: bpy.props.IntProperty(
        name="Suffix Digits",
        description="Defines the number of digits used for numerating.",
        default=3,
    )

    # Collider Shapes
    box_shape: bpy.props.StringProperty(name="Box Collider", default="UBX",
                                        description='Naming used to define box colliders')
    sphere_shape: bpy.props.StringProperty(name="Sphere Collider", default="USP",
                                           description='Naming used to define sphere colliders')
    capsule_shape: bpy.props.StringProperty(name="Capsule Collider", default="UCP",
                                            description='Naming used to define capsule colliders')
    convex_shape: bpy.props.StringProperty(name="Convex Collider", default="UCX",
                                           description='Naming used to define convex colliders')
    mesh_shape: bpy.props.StringProperty(name="Mesh Collider", default="",
                                         description='Naming used to define triangle mesh colliders')

    # Rigid Body
    rigid_body_naming_position: bpy.props.EnumProperty(
        name='Parent Extension',
        items=(('PREFIX', "Prefix", "Prefix"),
               ('SUFFIX', "Suffix", "Suffix")),
        default='SUFFIX',
        description='Add custom naming as prefix or suffix'
    )

    rigid_body_extension: bpy.props.StringProperty(name="Parent Extension", default="RB",
                                                   description='String added to the parent naming')

    rigid_body_separator: bpy.props.StringProperty(name="Separator", default="_",
                                                   description="Separator character used to divide different suffixes (Empty field removes the separator from the naming)")

    # Collider Groups
    collider_groups_enabled: bpy.props.BoolProperty(
        name='Enable Collider Groups', description='', default=True)

    user_group_01_name: bpy.props.StringProperty(name="Display Name", default="Simple",
                                                 description='Naming of User Collider Group 01')
    user_group_02_name: bpy.props.StringProperty(name="Display Name", default="Simple 2",
                                                 description='Naming of User Collider Group 02')
    user_group_03_name: bpy.props.StringProperty(name="Display Name", default="Complex",
                                                 description='Naming of User Collider Group 03')

    user_group_01: bpy.props.StringProperty(name="Pre/Suffix", default="",
                                            description='Naming of User Collider Group 01')
    user_group_02: bpy.props.StringProperty(name="Pre/Suffix", default="",
                                            description='Naming of User Collider Group 02')
    user_group_03: bpy.props.StringProperty(name="Pre/Suffix", default="Complex",
                                            description='Naming of User Collider Group 03')

    # MATERIALS
    use_physics_material: bpy.props.BoolProperty(
        name='Enable Physics Materials List', description='', default=False)

    skip_material: bpy.props.BoolProperty(
        name='Skip Physics Material', description='Skip the generation and assignment of physics materials',
        default=False)

    material_naming_position: bpy.props.EnumProperty(
        name='Physics Material',
        items=(('PREFIX', "Prefix", "Prefix"),
               ('SUFFIX', "Suffix", "Suffix")),
        default='PREFIX',
        description='Add custom naming as prefix or suffix'
    )

    physics_material_separator: bpy.props.StringProperty(name="Separator", default="_",
                                                         description="Separator character used between material name and suffix/prefix")

    use_custom_mat_suf_prefix: bpy.props.BoolProperty(name='Use Suffix/Prefix',
                                                      description='',
                                                      default=False)

    use_random_color: bpy.props.BoolProperty(name="Use Random Color", default=True)

    physics_material_su_prefix: bpy.props.StringProperty(name="Collider Prefix", default="",
                                                         description='Simple string added to the beginning of the collider suffix/prefix')

    physics_material_name: bpy.props.StringProperty(name='Default Physics Material',
                                                    default='MI_COL',
                                                    # type=bpy.types.Material,
                                                    # poll=scene_my_collision_material_poll,
                                                    description='Physical Materials are used in game engines to define different responses of a physical object when interacting with other elements of the game world. They can be used to trigger different audio, VFX or gameplay events depending on the material. Simple Collider will create a simple semi transparent material called "COL_DEFAULT" if no material is assigned')

    physics_material_filter: bpy.props.StringProperty(name='Physics Material Filter',
                                                      default="COL",
                                                      description='By default, the Physics Material input shows all materials of the blender scene. Use the filter to only display materials that contain the filter characters in their name. E.g.,  Using the filter "COL", all materials that do not have "COL" in their name will be hidden from the physics material selection', )

    ###################################################################
    # UI

    # The object color for the bounding object
    user_group_01_color: bpy.props.FloatVectorProperty(name="User Group 1 Color",
                                                       description="Object color and alpha for User Collider Group 01",
                                                       default=(0.36, 0.5, 1), min=0.0, max=1.0,
                                                       subtype='COLOR', size=3)

    # The object color for the bounding object
    user_group_02_color: bpy.props.FloatVectorProperty(name="User Group 2 Color",
                                                       description="Object color and alpha for User Collider Group 02",
                                                       default=(0.5, 1, 0.36), min=0.0, max=1.0, subtype='COLOR',
                                                       size=3)

    # The object color for the bounding object
    user_group_03_color: bpy.props.FloatVectorProperty(name="User Group 3 Color",
                                                       description="Object color and alpha for User Collider Group 03.",
                                                       default=(1, 0.36, 0.36), min=0.0, max=1.0, subtype='COLOR',
                                                       size=3)

    # The object color for the bounding object
    user_groups_alpha: bpy.props.FloatProperty(name="Alpha",
                                               description="Object alpha for User Collider Groups.",
                                               default=0.5, min=0.0, max=1.0)

    # Modal Box
    use_modal_box: bpy.props.BoolProperty(name="Use Backdrop", default=True)

    modal_box_color: bpy.props.FloatVectorProperty(name="Backdrop Color",
                                                   description="Object color and alpha for User Collider Group 03.",
                                                   default=(0.2, 0.2, 0.2, 0.5), min=0.0, max=1.0, subtype='COLOR',
                                                   size=4)

    # Modal Fonts
    modal_color_default: bpy.props.FloatVectorProperty(name="Default",
                                                       description="Font color in the 3D viewport for settings that are reset every time the collision operator is called",
                                                       default=(1.0, 1.0, 1.0, 1), min=0.0, max=1.0,
                                                       subtype='COLOR', size=4)

    modal_color_title: bpy.props.FloatVectorProperty(name="Title",
                                                     description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_highlight: bpy.props.FloatVectorProperty(name="Active Highlight",
                                                         description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                         default=(0.0, 1.0, 1.0, 1.0), min=0.0, max=1.0,
                                                         subtype='COLOR', size=4)

    modal_color_error: bpy.props.FloatVectorProperty(name="Invalid Input",
                                                     description="Font color in the 3D viewport the title when an error occurs",
                                                     default=(1.0, 0.0, 0.0, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_modal: bpy.props.FloatVectorProperty(name="Modal",
                                                     description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(1.0, 1.0, 0.5, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_bool: bpy.props.FloatVectorProperty(name="Bool",
                                                    description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(1.0, 1.0, 0.75, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_color_enum: bpy.props.FloatVectorProperty(name="Enum",
                                                    description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
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
                                                      default=get_default_executable_path(),
                                                      subtype='FILE_PATH',
                                                      )

    executable_path: bpy.props.StringProperty(name='Overwrite Executable',
                                              description='Specify a path to another V-hacd executable if you want to use a custom build',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(name='Temporary Data Path',
                                        description='Data path to store temporary files like meshes and log files used by V-Hacd to generate Auto Convex colliders',
                                        default=setDefaultTemp(), maxlen=1024, subtype='DIR_PATH')

    # VHACD parameters

    # -e
    vhacd_volumneErrorPercent: bpy.props.FloatProperty(name='Volumne Error Percentage',
                                                       description=' Volume error allowed as a percentage. Default is 1%. Valid range is 0.001 to 10',
                                                       default=0.01,
                                                       min=0.001,
                                                       max=10)

    # -l minEdgeLength      : Minimum size of a voxel edge. Default value is 2 voxels.
    vhacd_minEdgeLength: bpy.props.FloatProperty(name="Min Voxel Edge Size",
                                                 description="Minimum size of a voxel edge. Default value is 2 voxels",
                                                 default=2,
                                                 min=0)

    # -d
    vhacd_maxRecursionDepth: bpy.props.IntProperty(name='Maximum recursion depth',
                                                   description="The recursion depth has reached a maximum limit specified by the user.  A value of 12 results in a maximum of 4,096 convex hulls",
                                                   default=10,
                                                   min=2,
                                                   max=64)

    # -f
    vhacd_fillMode: bpy.props.EnumProperty(name='Fill Mode',
                                           description="Fill Mode defines the method used for finding the interior voxels used for the auto convex collider creation",
                                           items=(('raycast', 'Raycast',
                                                   'If the source mesh is not perfectly watertight, the user can try the raycast fill option, which will determine interior voxels by raycasting towards the source mesh'),
                                                  ('flood', 'Flood',
                                                   'V-HACD will find all of the interior voxels by performing a flood-fill operation. If the source mesh is not 100% perfectly watertight, the flood-fill will fail'),
                                                  ('surface', 'Surface',
                                                   'In some cases, a user might actually want the source mesh to be treated as if it were hollow, in which case they can skip generating interior voxels entirely')),
                                           default='raycast')

    # -p <true/false>         : If false, splits hulls in the middle. If true, tries to find optimal split plane location. False by default.
    vhacd_optimalSplitPlane: bpy.props.BoolProperty(name="Optimal Split Plane",
                                                    default=False,
                                                    description="If false, splits hulls in the middle. If true, tries to find optimal split plane location. False by default")

    wireframe_mode: bpy.props.EnumProperty(name="Wireframe Mode",
                                           items=(('OFF', "Off",
                                                   "Colliders show no wireframes"),
                                                  ('PREVIEW', "Preview",
                                                   "Collider wireframes are only visible during the generation"),
                                                  ('ALWAYS', "Always",
                                                   "Collider wireframes are visible during the generation and remain afterwards")),
                                           description="Set the display type for collider wireframes",
                                           default='ALWAYS')

    my_hide: bpy.props.BoolProperty(name="Hide After Creation",
                                    description="Hide collider after creation.",
                                    default=False)

    # DEBUG
    debug: bpy.props.BoolProperty(name="Debug Mode",
                                  description="Debug mode only used for debuging during development",
                                  default=False)
    general_props = [
        "fix_parent_inverse_mtrx",
        "use_parent_to",
        "keep_modifier_defaults",
    ]

    props = [
        "separator",
        "collision_string_prefix",
        "collision_string_suffix",
        "collision_digits",
    ]

    props_shapes = [
        "box_shape",
        "sphere_shape",
        "capsule_shape",
        "convex_shape",
        "mesh_shape",
    ]

    props_parent = [
        "rigid_body_separator",
        "rigid_body_naming_position",
        "rigid_body_extension",
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
    ]

    props_advanced_physics_materials = [
        "physics_material_filter",
        "physics_material_separator",
        "physics_material_su_prefix",
        "use_random_color",
    ]

    col_props = [
        "use_col_collection",
        "col_collection_name",
        "col_collection_color",
    ]

    ui_col_colors = [
        'user_group_01_color',
        'user_group_02_color',
        'user_group_03_color',
        'user_groups_alpha',
    ]

    ui_props = [
        "modal_font_size",
        "use_modal_box",
        "modal_box_color",
        "modal_color_title",
        "modal_color_highlight",
        "modal_color_error",
        "modal_color_modal",
        "modal_color_bool",
        "modal_color_default",
        "modal_color_enum",
    ]

    vhacd_props_config = [
        "vhacd_volumneErrorPercent",
        "vhacd_minEdgeLength",
        "vhacd_maxRecursionDepth",
        "vhacd_fillMode",
        "vhacd_optimalSplitPlane",
    ]

    display_config = [
        "my_hide",
        "wireframe_mode",
    ]

    def keymap_ui(self, layout, title, property_prefix, id_name, properties_name):
        box = layout.box()
        split = box.split(align=True, factor=0.5)
        col = split.column()

        # Is hotkey active checkbox
        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_active', text="")
        row.label(text=title)

        # Button to assign the key assignments
        col = split.column()
        row = col.row(align=True)
        key_type = getattr(self, f'{property_prefix}_type')
        text = (
            bpy.types.Event.bl_rna.properties['type'].enum_items[key_type].name
            if key_type != 'NONE'
            else 'Press a key'
        )

        op = row.operator("collision.key_selection_button", text=text)
        op.property_prefix = property_prefix

        # row.prop(self, f'{property_prefix}_type', text="")
        op = row.operator("collision.remove_hotkey", text="", icon="X")
        op.idname = id_name
        op.properties_name = properties_name
        op.property_prefix = property_prefix

        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_ctrl')
        row.prop(self, f'{property_prefix}_shift')
        row.prop(self, f'{property_prefix}_alt')

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':

            box = layout.box()
            row = box.row()
            row.label(text='General')



            for propName in self.general_props:
                row = box.row()
                row.prop(self, propName)

            box = layout.box()
            row = box.row()
            row.label(text='Collections')

            for propName in self.col_props:
                row = box.row()
                row.prop(self, propName)

            box = layout.box()
            row = box.row(align=True)
            row.label(text="Collider Display")

            for propName in self.display_config:
                row = box.row()
                row.prop(self, propName)

            row = layout.row()
            row.prop(self, 'debug')

        if self.prefs_tabs == 'NAMING':
            box = layout.box()
            row = box.row()
            row.label(text="Default Presets")
            row = box.row(align=True)
            for preset_name in presets.keys():
                op = row.operator(SetSimpleColliderPreferencesOperator.bl_idname, text=f"{preset_name}")
                op.preset_name = preset_name
            row = box.row(align=True)
            row.label(text="User Presets")
            row = box.row(align=True)
            op = row.operator('object.upgrade_simple_collider_presets')
            row = box.row(align=True)
            row.menu('OBJECT_MT_collision_presets',
                     text=OBJECT_MT_collision_presets.bl_label)
            row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
            row.operator(COLLISION_preset.bl_idname, text="",
                         icon='REMOVE').remove_active = True
            row.operator("wm.url_open", text="",
                         icon='HELP').url = "https://weisl.github.io/collider_import_engines/"

            from ..ui.properties_panels import collider_presets_folder
            row.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = collider_presets_folder()

            box_name = box.box()
            row = box.row()
            row.prop(self, "naming_position", expand=True)

            row = box_name.row()
            if self.naming_position == 'PREFIX':
                row.label(
                    text="Name = Collider Prefix + Shape + Group + Collider Suffix + Basename + Numbering")
            else:  # self.naming_position == 'SUFFIX':
                row.label(
                    text="Name = Basename + Collider Prefix + Shape + Group + Collider Suffix + Numbering")

            row = box_name.row()
            row.label(text="E.g. " + OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier='box_shape',
                                                                                       user_group='USER_01',
                                                                                       basename='Suzanne'))

            row = box.row()
            row.prop(self, "replace_name")

            row = box.row()

            if not self.replace_name:
                row.enabled = False
            row.prop(self, "obj_basename")

            for propName in self.props:
                row = box.row()
                row.prop(self, propName)

            box2 = layout.box()
            box2.label(text="Shape")
            for propName in self.props_shapes:
                row = box2.row()
                row.prop(self, propName)

            box = layout.box()
            box.label(text="Rigid Body")

            for propName in self.props_parent:
                row = box.row()
                row.prop(self, propName)

            box = layout.box()
            box.label(text="Collider Groups")

            for propName in self.props_collider_groups:
                row = box.row()
                row.prop(self, propName)

            col = box.column()
            if not self.collider_groups_enabled:
                col.enabled = False

            for count, (prop_01, prop_02) in enumerate(
                    zip(self.props_collider_groups_name, self.props_collider_groups_identifier), start=1):
                split = col.split(align=True, factor=0.1)
                split.label(text=f"Group_{str(count)}:")

                split = split.split(align=True, factor=0.5)
                split.prop(self, prop_01)
                split.prop(self, prop_02)

            box = layout.box()
            box.label(text="Physics Materials")

            for propName in self.props_physics_materials:
                row = box.row()
                row.prop(self, propName)

            box = box.box()
            row = box.row()
            row.prop(self, "use_physics_material")

            row = box.row()
            row.prop(self, "skip_material")

            col = box.column()
            if not self.use_physics_material:
                col.enabled = False

            row = col.row()
            row.prop(self, "material_naming_position", expand=True)
            for propName in self.props_advanced_physics_materials:
                row = col.row()
                row.prop(self, propName)



        elif self.prefs_tabs == 'KEYMAP':
            from .keymap import keymaps_items_dict
            for key, value in keymaps_items_dict.items():
                self.keymap_ui(layout, key, value['name'], value['idname'], value['operator'])


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
            text = "Auto convex is only supported for Windows and Linux at this moment."
            texts = [text]
            if platform.system() not in ['Windows', 'Linux']:
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
            row.operator("wm.url_open", text="",
                         icon='URL').url = "https://github.com/kmammou/v-hacd"

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

        elif self.prefs_tabs == 'SUPPORT':
            # Cross Promotion
            box = layout.box()

            ### SIMPLE Camera Manager
            col = box.column(align=True)
            row = col.row()
            row.label(text="♥♥♥ Leave a Review or Rating! ♥♥♥")
            row = col.row()
            row.label(text='Support & Feedback')
            row = col.row(align=True)
            row.label(text="Simple Collider")
            row.operator("wm.url_open", text="Superhive",
                         icon="URL").url = "https://superhivemarket.com/products/simple-collider"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_collider"

            col = box.column(align=True)
            row = col.row()
            row.label(text='Join the Discussion!')
            row = col.row()
            row.operator("wm.url_open", text="Join Discord", icon="URL").url = "https://discord.gg/VRzdcFpczm"


            ### SIMPLE TOOLS PROMOTION

            box = layout.box()
            col = box.column(align=True)
            text = "Explore my other Blender Addons designed for more efficient game asset workflows!"
            label_multiline(
                context=context,
                text=text,
                parent=col
            )

            box.label(text="Simple Tools ($)")
            col = box.column(align=True)

            row = col.row(align=True)
            row.label(text="Simple Camera Manager")
            row.operator("wm.url_open", text="Superhive",
                         icon="URL").url = "https://superhivemarket.com/products/simple-camera-manager"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_camera_manager"

            row = col.row(align=True)
            row.label(text="Simple Export")
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_export"

            box.label(text="Simple Tools (Free)")
            col = box.column(align=True)
            row = col.row(align=True)
            row.label(text="Simple Renaming")
            row.operator("wm.url_open", text="Blender Extensions",
                         icon="URL").url = "https://extensions.blender.org/add-ons/simple-renaming-panel/"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_renaming"


classes = (
    CollisionAddonPrefs,
)


@persistent
def _load_handler(dummy):
    """
    Handler function that is called when a new Blender file is loaded.
    This function sets the default active material and default group values.
    """
    set_default_active_mat()
    set_default_group_values()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_panel_category(None, bpy.context)

    # Append the load handler to be executed after loading a Blender file
    bpy.app.handlers.load_post.append(_load_handler)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # Remove the load handler
    bpy.app.handlers.load_post.remove(_load_handler)
