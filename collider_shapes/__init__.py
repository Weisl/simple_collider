import bpy

from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_primitive
from . import add_bounding_sphere
from . import add_collision_mesh
from . import add_minimum_bounding_box


def update_display_colliders(self, context):
    for obj in bpy.data.objects:
        if obj.get('isCollider'):
            obj.display_type = self.display_type
    return {'FINISHED'}


classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_minimum_bounding_box.OBJECT_OT_add_aligned_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    add_bounding_sphere.OBJECT_OT_add_bounding_sphere,
    add_bounding_convex_hull.OBJECT_OT_add_convex_hull,
    add_collision_mesh.OBJECT_OT_add_mesh_collision,
)


def register():
    scene = bpy.types.Scene
    obj = bpy.types.Object

    # Display setting of the bounding object in the viewport
    scene.my_hide = bpy.props.BoolProperty(name="Hide After Creation",
                                           description="Hide Bounding Object After Creation.", default=False)

    # Tranformation space to be used for creating the bounding object.
    scene.my_space = bpy.props.EnumProperty(name="Generation Axis",
                                            items=(('LOCAL', "Local",
                                                    "Generate the collision based on the local space of the object vertices."),
                                                   ('GLOBAL', "Global",
                                                    "Generate the collision based on the global space of the object vertices.")),
                                            default="LOCAL")

    scene.display_type = bpy.props.EnumProperty(name="Collider Display",
                                                items=(
                                                    ('SOLID', "Solid", "Display the colliders as solid"),
                                                    ('WIRE', "Wire", "Display the colliders as wireframe"),
                                                ),
                                                default="SOLID",
                                                update=update_display_colliders)

    scene.wireframe_mode = bpy.props.EnumProperty(name="Wireframe Mode",
                                                  items=(('OFF', "Off",
                                                          "There is no wireframe preview on the collision mesh."),
                                                         ('PREVIEW', "Preview",
                                                          "The wireframes are only visible during the generation."),
                                                         ('ALWAYS', "Always",
                                                          "The wireframes remain visible afterwards.")),
                                                  description="Hide Bounding Object After Creation.", default='PREVIEW')

    # OBJECT
    obj.basename = bpy.props.StringProperty(default='geo', name='Basename',
                                            description='Default naming used for collisions when the name is not inherited from a parent (Name from parent is disabled).')

    obj.collider_type = bpy.props.EnumProperty(name="Shading",
                                               items=[('BOX', "Box", "Used to descibe boxed shape collision shapes."),
                                                      (
                                                          'SHERE', "Sphere",
                                                          "Used to descibe spherical collision shapes."),
                                                      ('CONVEX', "CONVEX",
                                                       "Used to descibe convex shaped collision shapes."),
                                                      ('MESH', "Triangle Mesh",
                                                       "Used to descibe complex triangle mesh collisions.")],
                                               default='BOX')

    obj.collider_complexity = bpy.props.EnumProperty(name="collider complexity", items=[
        ('USER_01', "Simple Complex",
         "(Simple and Complex) Custom value to distinguish different types of collisions in a game engine."),
        ('USER_02', "Simple", "(Simple) Custom value to distinguish different types of collisions in a game engine."),
        (
            'USER_03', "Complex",
            "(Complex) Custom value to distinguish different types of collisions in a game engine.")],
                                                     default="USER_01")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    scene.visibility_toggle_list = []




def unregister():
    scene = bpy.types.Scene
    obj = bpy.types.Object

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete custom properties on unregister
    del scene.wireframe_mode
    del scene.my_space
    del scene.my_hide

    del obj.collider_complexity
    del obj.collider_type
    del obj.basename
