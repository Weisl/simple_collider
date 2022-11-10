from . import user_groups

classes = (
    user_groups.ColliderGroup,
    user_groups.COLLISION_OT_assign_user_group,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
