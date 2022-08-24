import bpy
from . import user_groups

classes = (
    user_groups.ColliderGroup,
    user_groups.COLLISION_OT_assign_user_group,
)

def register():
    scene = bpy.types.Scene

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Pointer Properties have to be initialized after classes
    scene.visibility_toggle_all = bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    scene.visibility_toggle_obj = bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    scene.visibility_toggle_user_group_01 = bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    scene.visibility_toggle_user_group_02 = bpy.props.PointerProperty(type=user_groups.ColliderGroup)
    scene.visibility_toggle_user_group_03 = bpy.props.PointerProperty(type=user_groups.ColliderGroup)


def unregister():
    scene = bpy.types.Scene

    del scene.visibility_toggle_user_group_03
    del scene.visibility_toggle_user_group_02
    del scene.visibility_toggle_user_group_01
    del scene.visibility_toggle_obj
    del scene.visibility_toggle_all

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
