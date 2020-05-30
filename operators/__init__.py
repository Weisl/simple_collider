from . import add_bounding_box
from . import add_bounding_cylinder
from . import add_bounding_primitive

classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
