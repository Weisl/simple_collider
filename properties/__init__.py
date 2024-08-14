import bpy

from .properties import ColliderTools_Properties

classes = (
    properties.ColliderTools_Properties,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    # Pointer Properties have to be initialized after classes
    scene = bpy.types.Scene
    scene.simple_collider = bpy.props.PointerProperty(
        type=ColliderTools_Properties)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    del scene.simple_collider
