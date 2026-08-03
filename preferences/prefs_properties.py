import bpy
import os

from .keymap import keymaps_items_dict
from .preferences import update_panel_category, update_keymap, update_group_colors
from .preferences import get_default_executable_path, setDefaultTemp
from .preferences import get_default_coacd_executable_path
from .preferences import collection_colors
from ..properties.constants import PRESETFOLDER, DEFAULT_PRESET
from .. import __package__ as base_package

def setdefaultpreset():
    # Replicate the logic of get_simple_collider_preset_files to get the list of files
    preset_folder = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", PRESETFOLDER)
    # Create the folder if it doesn't exist
    os.makedirs(preset_folder, exist_ok=True)
    # Check if the user has specified a custom preset folder
    py_files = [f for f in os.listdir(preset_folder) if f.endswith('.py')]
    try:
        return py_files.index(DEFAULT_PRESET)
    except ValueError:
        return 0  # Fallback to first item if not found


def get_simple_collider_preset_files(self, context):
    """Get a list of available preset files for simple export."""
    preset_folder = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", PRESETFOLDER)

    # Check if the user has specified a custom preset folder
    prefs = context.preferences.addons[base_package].preferences
    if prefs.preset_path_override and os.path.isdir(bpy.path.abspath(prefs.preset_path_override)):
        preset_folder = bpy.path.abspath(prefs.preset_path_override)

    from ..presets.preset_operator import get_py_files
    return get_py_files(self, context, preset_folder)



class CollisionAddonPrefsProperties():

    prefs_tabs: bpy.props.EnumProperty(
        name='Collider Settings',
        items=(('SETTINGS', "General", "General addon settings"),
               ('POSTPROCESS', "Post Processing", "Settings for automatic post-processing of newly created colliders."),
               ('NAMING', "Presets", "Presets settings: Create, change and modify presets"),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon."),
               ('UI', "Ui", "Settings related to the Ui and display of the addon."),
               ('VHACD', "Auto Convex", "Settings related to Auto Convex generation (V-HACD and CoACD)."),
               ('VALIDATION', "Validation", "Settings for the collider validation checks."),
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

    # Auto-apply Collider Cleanup operations right after collider creation
    auto_apply_tris_limit: bpy.props.BoolProperty(name="Auto Apply Tris Count",
                                                   description="Automatically limit newly created colliders to the target triangle count below",
                                                   default=False)

    auto_apply_max_triangle_count: bpy.props.IntProperty(name="Target Triangles",
                                                          description="Target triangle count used when auto-applying the triangle count limit",
                                                          default=800,
                                                          min=1)

    auto_apply_origin_to_parent: bpy.props.BoolProperty(name="Auto Apply Origin to Parent",
                                                         description="Automatically move newly created colliders' origin to match their parent's, for engines that require matching origins",
                                                         default=False)

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

    simple_collider_default_preset: bpy.props.EnumProperty(
        name="Simple Default Preset",
        description="Select a default preset",
        items=lambda self, context: get_simple_collider_preset_files(self, context),
        default=setdefaultpreset()
    )

    preset_path_override: bpy.props.StringProperty(
        name="Overwrite Preset Folder",
        description="Override the default Blender preset folder",
        subtype='DIR_PATH',
    )

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
        min=0,
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
    voxel_shape: bpy.props.StringProperty(name="Voxel Collider", default="UVX",
                                          description='Naming used to define voxel grid colliders')

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
                                                       default=(0.4235, 0.8902, 0.4745), min=0.0, max=1.0,
                                                       subtype='COLOR', size=3, update=update_group_colors)

    # The object color for the bounding object
    user_group_02_color: bpy.props.FloatVectorProperty(name="User Group 2 Color",
                                                       description="Object color and alpha for User Collider Group 02",
                                                       default=(0.4745, 0.4235, 0.8902), min=0.0, max=1.0, subtype='COLOR',
                                                       size=3, update=update_group_colors)

    # The object color for the bounding object
    user_group_03_color: bpy.props.FloatVectorProperty(name="User Group 3 Color",
                                                       description="Object color and alpha for User Collider Group 03.",
                                                       default=(0.8902, 0.4745, 0.4235), min=0.0, max=1.0, subtype='COLOR',
                                                       size=3, update=update_group_colors)

    # The object color for the bounding object
    user_groups_alpha: bpy.props.FloatProperty(name="Alpha",
                                               description="Object alpha for User Collider Groups.",
                                               default=0.5, min=0.0, max=1.0, update=update_group_colors)

    # Modal Box
    use_modal_box: bpy.props.BoolProperty(name="Use Backdrop", default=True)

    modal_box_color: bpy.props.FloatVectorProperty(name="Backdrop Color",
                                                   description="Object color and alpha for User Collider Group 03.",
                                                   default=(0.141, 0.149, 0.176, 0.85), min=0.0, max=1.0, subtype='COLOR',
                                                   size=4)

    # Modal Fonts
    modal_color_default: bpy.props.FloatVectorProperty(name="Default",
                                                       description="Font color in the 3D viewport for settings that are reset every time the collision operator is called",
                                                       default=(0.910, 0.914, 0.933, 1.0), min=0.0, max=1.0,
                                                       subtype='COLOR', size=4)

    modal_color_title: bpy.props.FloatVectorProperty(name="Title",
                                                     description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(0.133, 0.773, 0.369, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_highlight: bpy.props.FloatVectorProperty(name="Active Highlight",
                                                         description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                         default=(0.133, 0.773, 0.369, 1.0), min=0.0, max=1.0,
                                                         subtype='COLOR', size=4)

    modal_color_error: bpy.props.FloatVectorProperty(name="Invalid Input",
                                                     description="Font color in the 3D viewport the title when an error occurs",
                                                     default=(0.937, 0.267, 0.267, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_navigation: bpy.props.FloatVectorProperty(name="Ignore Input / Navigation",
                                                          description="Font color in the 3D viewport for the whole line while input is being ignored (ALT) or while navigating the viewport",
                                                          default=(0.604, 0.616, 0.651, 0.7), min=0.0, max=1.0,
                                                          subtype='COLOR', size=4)

    modal_color_modal: bpy.props.FloatVectorProperty(name="Modal",
                                                     description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                     default=(0.910, 0.914, 0.933, 1.0), min=0.0, max=1.0,
                                                     subtype='COLOR', size=4)

    modal_color_bool: bpy.props.FloatVectorProperty(name="Bool",
                                                    description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(0.910, 0.914, 0.933, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_color_enum: bpy.props.FloatVectorProperty(name="Enum",
                                                    description="Font color in the 3D viewport for settings that remain after changing even when calling collision operator again",
                                                    default=(0.843, 0.851, 0.878, 1.0), min=0.0, max=1.0,
                                                    subtype='COLOR', size=4)

    modal_font_size: bpy.props.IntProperty(name='Font Size',
                                           description="Changes the font size in the 3D viewport when calling the modal collider_shapes to create different collision shapes",
                                           default=36)

    ###################################################################
    # VHACD
    # if platform.system() == 'Windows':
    default_executable_path: bpy.props.StringProperty(name='Default VHACD Build',
                                                      description='Path to the V-Hacd executable distributed with this addon. (read-only)',
                                                      default=get_default_executable_path(),
                                                      subtype='FILE_PATH',
                                                      )

    executable_path: bpy.props.StringProperty(name='Custom VHACD Build',
                                              description='Specify a path to another V-hacd executable if you want to use a custom build',
                                              default='',
                                              subtype='FILE_PATH'
                                              )

    data_path: bpy.props.StringProperty(name='Temporary Data Path',
                                        description='Data path to store temporary files like meshes and log files used by V-Hacd to generate Auto Convex colliders',
                                        default=setDefaultTemp(), maxlen=1024, subtype='DIR_PATH')

    # VHACD parameters

    # -e
    vhacd_volumneErrorPercent: bpy.props.FloatProperty(name='Volume Error Percentage',
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

    ###################################################################
    # COACD (Auto Convex BETA)

    coacd_default_executable_path: bpy.props.StringProperty(name='Default CoACD Build',
                                                             description='Path to the CoACD executable distributed with this addon. (read-only)',
                                                             default=get_default_coacd_executable_path(),
                                                             subtype='FILE_PATH',
                                                             )

    coacd_executable_path: bpy.props.StringProperty(name='Custom CoACD Build',
                                                     description='Specify a path to another CoACD executable if you want to use a custom build',
                                                     default='',
                                                     subtype='FILE_PATH'
                                                     )

    # CoACD parameters

    # -pm
    coacd_preprocessMode: bpy.props.EnumProperty(name='Preprocess Mode',
                                                 description='Manifold preprocessing mode',
                                                 items=(('auto', 'Auto',
                                                         'Automatically check the input mesh manifoldness and only preprocess if needed'),
                                                        ('on', 'On',
                                                         'Force turn on the manifold pre-processing'),
                                                        ('off', 'Off',
                                                         'Force turn off the manifold pre-processing. The input mesh must be 2-manifold solid')),
                                                 default='auto')

    # -pr
    coacd_prepResolution: bpy.props.IntProperty(name='Preprocess Resolution',
                                                description='Resolution used for the manifold preprocessing step (20~100)',
                                                default=50,
                                                min=20,
                                                max=100)

    # -mi
    coacd_mctsIterations: bpy.props.IntProperty(name='MCTS Iterations',
                                                description='Number of search iterations in the Monte Carlo Tree Search (60~2000)',
                                                default=150,
                                                min=60,
                                                max=2000)

    # -md
    coacd_mctsDepth: bpy.props.IntProperty(name='MCTS Max Depth',
                                           description='Maximum search depth in the Monte Carlo Tree Search (2~7)',
                                           default=2,
                                           min=2,
                                           max=7)

    # -mn
    coacd_mctsNodes: bpy.props.IntProperty(name='MCTS Max Nodes',
                                           description='Maximum number of child nodes in the Monte Carlo Tree Search (10~40)',
                                           default=10,
                                           min=10,
                                           max=40)

    # -r
    coacd_resolution: bpy.props.IntProperty(name='Hausdorff Sampling Resolution',
                                            description='Sampling resolution used for the Hausdorff distance calculation (1000~10000)',
                                            default=1000,
                                            min=1000,
                                            max=10000)

    # -nm
    coacd_noMerge: bpy.props.BoolProperty(name='Disable Merge',
                                          description='Disable the merge postprocessing step. Merging is recommended in most cases as it reduces the number of convex hulls',
                                          default=False)

    # --pca
    coacd_pca: bpy.props.BoolProperty(name='PCA Preprocessing',
                                      description='Enable PCA (Principal Component Analysis) pre-processing, which can improve results for elongated shapes',
                                      default=False)

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

    hide_render_on_creation: bpy.props.BoolProperty(name="Hide From Render",
                                                    description="Hide newly created colliders from rendering. "
                                                                "Disable to keep colliders render-visible, e.g. for "
                                                                "export pipelines that rely on the render flag",
                                                    default=True)

    ###################################################################
    # VALIDATION

    validate_check_missing_collider: bpy.props.BoolProperty(name="Missing Collider",
                                                             description="Flag render meshes that have no collider assigned",
                                                             default=True)

    validate_check_triangle_count: bpy.props.BoolProperty(name="Triangle Count",
                                                           description="Flag colliders whose triangle count exceeds the limit below",
                                                           default=True)

    validate_check_min_dimension: bpy.props.BoolProperty(name="Collider Too Small",
                                                         description="Flag colliders whose bounding box is smaller than the minimum dimension below",
                                                         default=True)

    validate_check_bbox_mismatch: bpy.props.BoolProperty(name="Bounding Box Mismatch",
                                                          description="Flag a render mesh whose colliders, combined, don't cover its bounding box. "
                                                                      "Colliders are considered together, not individually, since several often "
                                                                      "combine to represent one mesh (e.g. a torso box plus limb capsules)",
                                                          default=True)

    validate_check_too_many_colliders: bpy.props.BoolProperty(name="Too Many Colliders",
                                                               description="Flag a render mesh with more collider shapes assigned than the limit below",
                                                               default=True)

    validate_check_naming: bpy.props.BoolProperty(name="Naming Convention",
                                                  description="Flag colliders whose name doesn't match the configured naming convention",
                                                  default=True)

    validate_check_non_manifold: bpy.props.BoolProperty(name="Non-Manifold Geometry",
                                                         description="Flag colliders with non-manifold (not watertight) edges",
                                                         default=True)

    validate_check_physics_material: bpy.props.BoolProperty(name="Missing Physics Material",
                                                             description="Flag colliders with no physics material assigned",
                                                             default=True)

    validate_check_parent_hierarchy: bpy.props.BoolProperty(name="Parent Hierarchy",
                                                             description="Flag colliders that aren't parented to a render mesh",
                                                             default=True)

    validate_check_parent_inverse_matrix: bpy.props.BoolProperty(name="Parent Inverse Matrix",
                                                                  description="Flag colliders whose parent inverse matrix hasn't been reset. "
                                                                              "Exporters like FBX/glTF don't preserve it, so the collider can end "
                                                                              "up at the wrong location/rotation on export. Run Fix Parent Inverse "
                                                                              "Matrix to clear it",
                                                                  default=True)

    validate_check_flipped_normals: bpy.props.BoolProperty(name="Flipped Normals",
                                                            description="Flag colliders whose face winding is inverted (inside-out mesh)",
                                                            default=True)

    validate_check_convex_shape_mismatch: bpy.props.BoolProperty(name="Convex Shape Mismatch",
                                                                  description="Flag colliders marked as convex whose geometry is not actually convex. "
                                                                              "Heuristic (volume-based) - off by default since complex meshes can "
                                                                              "produce false positives",
                                                                  default=False)

    validate_check_box_shape_mismatch: bpy.props.BoolProperty(name="Box Shape Mismatch",
                                                               description="Flag colliders marked as a box whose geometry is not actually box-shaped. "
                                                                           "Heuristic (volume-based) - off by default since complex meshes can "
                                                                           "produce false positives",
                                                               default=False)

    validate_check_mesh_could_use_primitive: bpy.props.BoolProperty(name="Mesh Could Use a Primitive",
                                                                     description="Flag mesh colliders whose geometry is already convex or box-shaped, "
                                                                                 "suggesting a simpler primitive collider. Heuristic (volume-based) - "
                                                                                 "off by default since complex meshes can produce false positives",
                                                                     default=False)

    validate_check_collision_shape_mismatch: bpy.props.BoolProperty(name="Collision Shape Mismatch",
                                                                     description="Flag colliders whose assigned shape (box/sphere/convex hull) doesn't "
                                                                                 "suit the shape of their render mesh, e.g. a box collider on a ball-like "
                                                                                 "mesh. Heuristic (volume-based) - off by default since complex meshes "
                                                                                 "can produce false positives",
                                                                     default=False)

    validation_max_triangle_count: bpy.props.IntProperty(name="Max Triangle Count",
                                                         description="Maximum number of triangles allowed on a collider before it is flagged",
                                                         default=255,
                                                         min=1)

    validation_min_dimension: bpy.props.FloatProperty(name="Min Dimension",
                                                      description="Minimum bounding box dimension a collider can have before it is flagged as too small",
                                                      default=0.01,
                                                      min=0.0,
                                                      subtype='DISTANCE')

    validation_bbox_tolerance: bpy.props.FloatProperty(name="Bounding Box Tolerance",
                                                       description="Allowed relative difference between a render mesh's colliders (combined) and its own bounding box, as a fraction of the render mesh's bounding box diagonal",
                                                       default=0.25,
                                                       min=0.0,
                                                       max=1.0,
                                                       subtype='FACTOR')

    validation_max_collider_count: bpy.props.IntProperty(name="Max Collider Count",
                                                         description="Maximum number of collider shapes a single render mesh can have before it is flagged",
                                                         default=8,
                                                         min=1)

    validation_shape_tolerance: bpy.props.FloatProperty(name="Shape Tolerance",
                                                        description="Allowed relative volume difference for the convex/box shape checks and the "
                                                                    "mesh-could-use-a-primitive suggestion, as a fraction of the larger volume being compared",
                                                        default=0.02,
                                                        min=0.0,
                                                        max=1.0,
                                                        subtype='FACTOR')

    validation_sphere_tolerance: bpy.props.FloatProperty(name="Sphere Fit Tolerance",
                                                        description="Allowed relative volume difference between a render mesh and its exact minimum "
                                                                    "enclosing sphere, used only by the collision-shape-mismatch check's sphere test. "
                                                                    "Kept separate from, and looser than, Shape Tolerance because a low-poly but "
                                                                    "intentionally round mesh sits measurably under its ideal enclosing sphere's "
                                                                    "volume from facet flattening alone, unlike the exact hull/OBB volume "
                                                                    "comparisons the other checks use",
                                                        default=0.05,
                                                        min=0.0,
                                                        max=1.0,
                                                        subtype='FACTOR')

    postprocess_props = [
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
        "voxel_shape",
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
        "modal_color_navigation",
    ]

    vhacd_props_config = [
        "vhacd_volumneErrorPercent",
        "vhacd_minEdgeLength",
        "vhacd_maxRecursionDepth",
        "vhacd_fillMode",
        "vhacd_optimalSplitPlane",
    ]

    coacd_props_config = [
        "coacd_preprocessMode",
        "coacd_prepResolution",
        "coacd_mctsIterations",
        "coacd_mctsDepth",
        "coacd_mctsNodes",
        "coacd_resolution",
        "coacd_noMerge",
        "coacd_pca",
    ]

    display_config = [
        "my_hide",
        "wireframe_mode",
        "hide_render_on_creation",
    ]

    props_validation_checks = [
        "validate_check_missing_collider",
        "validate_check_triangle_count",
        "validate_check_min_dimension",
        "validate_check_bbox_mismatch",
        "validate_check_too_many_colliders",
        "validate_check_naming",
        "validate_check_non_manifold",
        "validate_check_flipped_normals",
        "validate_check_physics_material",
        "validate_check_parent_hierarchy",
        "validate_check_parent_inverse_matrix",
        "validate_check_convex_shape_mismatch",
        "validate_check_box_shape_mismatch",
        "validate_check_mesh_could_use_primitive",
        "validate_check_collision_shape_mismatch",
    ]

    props_validation_thresholds = [
        "validation_max_triangle_count",
        "validation_min_dimension",
        "validation_bbox_tolerance",
        "validation_max_collider_count",
        "validation_shape_tolerance",
        "validation_sphere_tolerance",
    ]