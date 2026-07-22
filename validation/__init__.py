import bpy

from . import operators
from . import properties

classes = (
    properties.ValidationIssueItem,
    operators.COLLISION_UL_validation_results,
    operators.COLLISION_OT_select_validation_object,
    operators.COLLISION_OT_copy_validation_report,
    operators.COLLISION_OT_validate_colliders,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.simple_collider_validation_results = bpy.props.CollectionProperty(type=properties.ValidationIssueItem)
    wm.simple_collider_validation_index = bpy.props.IntProperty()


def unregister():
    from bpy.utils import unregister_class

    wm = bpy.types.WindowManager
    del wm.simple_collider_validation_index
    del wm.simple_collider_validation_results

    for cls in reversed(classes):
        unregister_class(cls)
