import bpy

from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_primitive
from . import add_bounding_sphere
from . import add_collision_mesh
from . import add_minimum_bounding_box

classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_minimum_bounding_box.OBJECT_OT_add_aligned_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    add_bounding_sphere.OBJECT_OT_add_bounding_sphere,
    add_bounding_convex_hull.OBJECT_OT_add_convex_hull,
    add_collision_mesh.OBJECT_OT_add_mesh_collision,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    wm = bpy.types.WindowManager
    obj = bpy.types.Object

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete custom properties on unregister
    del wm.collider_tools.wireframe_mode
    del wm.collider_tools.my_space
    del wm.collider_tools.display_type
    del wm.collider_tools.my_hide
