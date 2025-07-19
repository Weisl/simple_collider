from . import utility_operators
from . import visibility_selection_deletion
from . import visibility_settings

classes = (
    visibility_selection_deletion.COLLISION_OT_Selection,
    visibility_selection_deletion.COLLISION_OT_Deletion,
    visibility_selection_deletion.COLLISION_OT_simple_select,
    visibility_selection_deletion.COLLISION_OT_simple_delete,
    visibility_selection_deletion.COLLISION_OT_complex_select,
    visibility_selection_deletion.COLLISION_OT_complex_delete,
    visibility_selection_deletion.COLLISION_OT_simple_complex_select,
    visibility_selection_deletion.COLLISION_OT_simple_complex_delete,
    visibility_selection_deletion.COLLISION_OT_all_select,
    visibility_selection_deletion.COLLISION_OT_all_delete,
    visibility_selection_deletion.COLLISION_OT_non_collider_select,
    visibility_selection_deletion.COLLISION_OT_non_collider_delete,
    visibility_settings.VIEW3D_OT_object_view,
    visibility_settings.VIEW3D_OT_material_view,
    utility_operators.COLLISION_OT_adjust_decimation,
    utility_operators.COLLISION_OT_MoveOriginToParentOperator,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
