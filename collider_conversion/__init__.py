from . import convert_to_collider
from . import convert_to_mesh
from . import regenerate_name
from . import convert_from_name

classes = (
    convert_to_collider.OBJECT_OT_convert_to_collider,
    convert_to_mesh.OBJECT_OT_convert_to_mesh,
    convert_from_name.OBJECT_OT_convert_from_name,
    regenerate_name.OBJECT_OT_regenerate_name,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
