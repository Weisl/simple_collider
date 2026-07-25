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


def _clear_results_on_load(dummy=None):
    """Results live on WindowManager, which isn't saved with the .blend file
    and isn't cleared automatically on load - without this, switching files
    leaves a stale report from the previous file on screen until the user
    manually re-runs Validate Colliders."""
    wm = bpy.context.window_manager
    if wm is not None:
        wm.simple_collider_validation_results.clear()
        wm.simple_collider_validation_index = 0


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.simple_collider_validation_results = bpy.props.CollectionProperty(type=properties.ValidationIssueItem)
    wm.simple_collider_validation_index = bpy.props.IntProperty()

    bpy.app.handlers.load_post.append(_clear_results_on_load)


def unregister():
    from bpy.utils import unregister_class

    bpy.app.handlers.load_post.remove(_clear_results_on_load)

    wm = bpy.types.WindowManager
    del wm.simple_collider_validation_index
    del wm.simple_collider_validation_results

    for cls in reversed(classes):
        unregister_class(cls)
