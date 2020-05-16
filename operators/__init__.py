from . import add_box_collider
from . import add_cylindrical_collider

classes = (
    add_box_collider.OBJECT_OT_add_box_collision,
    add_cylindrical_collider.OBJECT_OT_add_cylinder_per_object_collision,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
