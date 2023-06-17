import bpy
from ..groups import user_groups


def update_display_colliders(self, context):
    '''Toggle between solid and wireframe displaytype'''
    for obj in bpy.data.objects:
        if obj.get('isCollider'):
            obj.display_type = self.display_type


def update_wireframe(self, context):
    for ob in bpy.data.objects:
        if ob.get('isCollider') and ob.type == 'MESH':
            ob.show_wire = self.toggle_wireframe
    self.toggle_wireframe != self.toggle_wireframe


class ColliderTools_Properties(bpy.types.PropertyGroup):
    visibility_toggle_all: bpy.props.PointerProperty(
        type=user_groups.ColliderGroup)
    visibility_toggle_obj: bpy.props.PointerProperty(
        type=user_groups.ColliderGroup)
    visibility_toggle_user_group_01: bpy.props.PointerProperty(
        type=user_groups.ColliderGroup)
    visibility_toggle_user_group_02: bpy.props.PointerProperty(
        type=user_groups.ColliderGroup)
    visibility_toggle_user_group_03: bpy.props.PointerProperty(
        type=user_groups.ColliderGroup)

    # -h
    maxHullAmount: bpy.props.IntProperty(name='Hulls',
                                         description='Maximum number of output convex hulls',
                                         default=8, 
                                         min=1, 
                                         soft_max =128,
                                         max=4096)

    # -v
    maxHullVertCount: bpy.props.IntProperty(name='Verts per Piece',
                                            description='Maximum number of vertices in the output convex hull',
                                            default=16,
                                            min=8,
                                            max=4096,
                                            soft_max=128)
    # -r
    voxelResolution: bpy.props.IntProperty(name="Voxel Resolution",
                                           description=' Total number of voxels to use. Default is 100000',
                                           default=100000, min=100000, max=10000000)

    # -s
    vhacd_shrinkwrap: bpy.props.BoolProperty(name='Shrinkwrap',
                                             default=False,
                                             description='Whether or not to shrinkwrap output to source mesh')

    # Display setting of the bounding object in the viewport
    toggle_wireframe: bpy.props.BoolProperty(name="Toggle Wireframe",
                                             description="Toggle wireframe display for collider objects",
                                             default=False,
                                             update=update_wireframe)

    display_type: bpy.props.EnumProperty(name="Collider Display",
                                         items=(
                                             ('SOLID', "Solid",
                                              "Display the colliders as solid"),
                                             ('WIRE', "Wire",
                                              "Display the colliders as wireframe"),
                                         ),
                                         default="SOLID",
                                         update=update_display_colliders)

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

    default_keep_original_material: bpy.props.BoolProperty(name="Keep Original Materials",
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

    default_cylinder_axis: bpy.props.EnumProperty(name="Cylinder Orientation",
                                                  items=(('X', "X", "Cylinder gets aligned to the X axis."),
                                                         ('Y', "Y", "Cylinder gets aligned to the Y axis."),
                                                         ('Z', "Z", "Cylinder gets aligned to the Z axis.")),
                                                  description="Orientation of the cylindrical collider object",
                                                  default='Z')

    default_cylinder_segments: bpy.props.IntProperty(name="Cylinder Segments",
                                                     description="Amount of cylinder segments.",
                                                     min=3,
                                                     default=12,
                                                     )

    default_sphere_segments: bpy.props.IntProperty(name="Sphere Segments",
                                                   description="Amount of sphere segments.",
                                                   default=16,
                                                   )

    default_capsule_segments: bpy.props.IntProperty(name="Capsule Segments",
                                                   description="Amount of sphere segments.",
                                                   default=16,
                                                   )

    default_color_type: bpy.props.EnumProperty(name="Color Type",
                                         items=(('OBJECT', 'Collider Groups', 'Color Type: Collider Groups'),
                                                ('MATERIAL', 'Physics Material', 'Color Type: Physic Materials'),
                                                ('SINGLE', 'Single', 'Color Type: Single Color')),
                                         description="Set Color Type",
                                         default='OBJECT')

    material_list_index: bpy.props.IntProperty(name="Index for material list",
                                               min=0,
                                               default=0,
                                               # get=get_int,
                                               # set=set_int,
                                               )

    # register variables saved in the blender scene
    defaultMeshMaterial: bpy.props.PointerProperty(
        type=bpy.types.Material,
        name='Default Mesh Material',
        description='The default mesh material will be assigned to any mesh that is converted from a collider to a mesh object'
    )

