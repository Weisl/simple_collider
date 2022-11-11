import bpy
from ..groups import user_groups
from ..pyshics_materials import material_functions


def update_display_colliders(self, context):
    '''Toggle between solid and wireframe displaytype'''
    for obj in bpy.data.objects:
        if obj.get('isCollider'):
            obj.display_type = self.display_type


def get_int(self):
    if self.on_load:
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
        default_mat_name = prefs.physics_material_name

        if not bpy.data.materials.get(default_mat_name):
            mat = material_functions.create_default_material()
            self["material_list_index"] = list(bpy.data.materials).index(mat)
            self['on_load'] = False
            return self["material_list_index"]

    return self["material_list_index"]


def set_int(self, value):
    self["material_list_index"] = value


def update_wireframe(self, context):
    for ob in bpy.data.objects:
        if ob.get('isCollider') and ob.type == 'MESH':
            ob.show_wire = self.toggle_wireframe
    self.toggle_wireframe != self.toggle_wireframe


class ColliderTools_Properties(bpy.types.PropertyGroup):
    visibility_toggle_all: bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    visibility_toggle_obj: bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    visibility_toggle_user_group_01: bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    visibility_toggle_user_group_02: bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    visibility_toggle_user_group_03: bpy.props.PointerProperty(type=user_groups.ColliderGroup)

    # -h
    maxHullAmount: bpy.props.IntProperty(name='Hulls',
                                         description='Maximum number of output convex hulls.',
                                         default=8, min=1, max=256)

    # -v
    maxHullVertCount: bpy.props.IntProperty(name='Verts per Piece',
                                            description='Maximum number of vertices in the output convex hull. Default value is 64',
                                            default=16,
                                            min=4,
                                            max=64)
    # -r
    voxelResolution: bpy.props.IntProperty(name="Voxel Resolution",
                                           description=' Total number of voxels to use. Default is 100000',
                                           default=100000, min=10000, max=64000000)

    # Display setting of the bounding object in the viewport
    my_hide: bpy.props.BoolProperty(name="Hide After Creation",
                                    description="Hide collider after creation.",
                                    default=False)

    # Display setting of the bounding object in the viewport
    toggle_wireframe: bpy.props.BoolProperty(name="Toggle Wireframe",
                                             description="Toggle wireframe display for collider objects.",
                                             default=False,
                                             update=update_wireframe)

    display_type: bpy.props.EnumProperty(name="Collider Display",
                                         items=(
                                             ('SOLID', "Solid", "Display the colliders as solid"),
                                             ('WIRE', "Wire", "Display the colliders as wireframe"),
                                         ),
                                         default="SOLID",
                                         update=update_display_colliders)

    wireframe_mode: bpy.props.EnumProperty(name="Wireframe Mode",
                                           items=(('OFF', "Off",
                                                   "Colliders show no wireframes"),
                                                  ('PREVIEW', "Preview",
                                                   "Collider wireframes are only visible during the generation"),
                                                  ('ALWAYS', "Always",
                                                   "Collider wireframes are visible during the generation and remain afterwards")),
                                           description="Set the display type for collider wireframes",
                                           default='PREVIEW')
    
    shading_mode: bpy.props.EnumProperty(name="Color Type",
                                         items=(('OBJECT', 'Object', 'Color Type: Object'),
                                             ('MATERIAL', 'Material', 'Color Type: Material'),
                                             ('SINGLE', 'Single', 'Color Type: Single')),
                                         description="Set Color Type",
                                         default='OBJECT')

    # Tranformation space to be used for creating the bounding object.
    my_space: bpy.props.EnumProperty(name="Generation Space",
                                     items=(('LOCAL', "Local",
                                             "Generate colliders based on the local space of the object."),
                                            ('GLOBAL', "Global",
                                             "Generate the collision based on the global space of the object.")),
                                     default="LOCAL")

    # Tranformation space to be used for creating the bounding object.
    default_space: bpy.props.EnumProperty(name="Transform Space",
                                     items=(('LOCAL', "Local",
                                             "Generate colliders based on the local or object transform space."),
                                            ('GLOBAL', "Global",
                                             "Generate the collision based on the global space of the object.")),
                                     default="LOCAL")


    default_modifier_stack: bpy.props.BoolProperty(name="Use Modifier Stack",
                                                   default=False,
                                                   description="Set the default for using the modifier stack or not when creating colliders.")

    default_user_group: bpy.props.EnumProperty(name="Default User Group",
                                               items=(('USER_01', "User Group 01",
                                                       "Show/Hide all objects that are part of User Group 01", '', 4),
                                                      ('USER_02', "User Group 02",
                                                       "Show/Hide all objects that are part of User Group 02", '', 8),
                                                      ('USER_03', "User Group 03",
                                                       "Show/Hide all objects that are part of User Group 03", '', 16)),
                                               default='USER_01')

    default_creation_mode: bpy.props.EnumProperty(name="Creation Mode",
                                                  items=(('INDIVIDUAL', "Individual",
                                                          "Colliders are created per individual object."),
                                                         ('SELECTION', "Selection",
                                                          "Colliders are created for the entire selection.")),
                                                  description="Colliders are generated per individual object or bounding the entire selection.",
                                                  default='INDIVIDUAL')

    on_load: bpy.props.BoolProperty(name='On Load',
                                    default=True)

    material_list_index: bpy.props.IntProperty(name="Index for material list",
                                               min=0,
                                               get=get_int,
                                               set=set_int,
                                               )

    # register variables saved in the blender scene
    defaultMeshMaterial: bpy.props.PointerProperty(
        type=bpy.types.Material,
        name='Default Mesh Material',
        description='The default mesh material will be assigned to any mesh that is converted from a collider to a mesh object'
    )
