import bpy

from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_primitive
from . import add_bounding_sphere
from . import add_collision_mesh
from . import add_minimum_bounding_box

def update_display_colliders(self, context):
    '''Toggle between solid and wireframe displaytype'''
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
                                           description="Hide collider after creation.", default=False)

    # Tranformation space to be used for creating the bounding object.
    scene.my_space = bpy.props.EnumProperty(name="Generation Axis",
                                            items=(('LOCAL', "Local",
                                                    "Generate colliders based on the local space of the object."),
                                                   ('GLOBAL', "Global",
                                                    "Generate the collision based on the global space of the object.")),
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
                                                          "Colliders show no wireframe"),
                                                         ('PREVIEW', "Preview",
                                                          "Collider wireframes are only visible during the generation"),
                                                         ('ALWAYS', "Always",
                                                          "Collider wireframes are visible during the generation and remain afterwards")),
                                                  description="Set the display type for collider wireframes",
                                                  default='PREVIEW')



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
    del scene.display_type
    del scene.my_hide

