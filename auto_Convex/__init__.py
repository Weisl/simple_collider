from . import add_bounding_auto_convex

classes = (
    add_bounding_auto_convex.VHACD_OT_convex_decomposition,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
