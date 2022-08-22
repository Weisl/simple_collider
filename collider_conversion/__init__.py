from . import conversion_operators

classes = (
    conversion_operators.OBJECT_OT_convert_to_collider,
    conversion_operators.OBJECT_OT_convert_to_mesh,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)