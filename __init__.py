bl_info = {
    "name": "CollisionTool",
    "description": "",
    "author": "Matthias Patscheider",
    "version": (0, 5, 0),
    "blender": (2, 81, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object"}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(preferences)
    importlib.reload(box_collider)
    importlib.reload(cylindrical_collider)
    importlib.reload(panels)
    importlib.reload(utils)
else:
    from . import preferences
    from . import box_collider
    from . import cylindrical_collider
    from . import panels
    from . import utils

import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
)
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

classes = (
    preferences.CollisionAddonPrefs,
    box_collider.OBJECT_OT_add_box_collision,
    cylindrical_collider.OBJECT_OT_add_cylinder_per_object_collision,
    # operators.OBJECT_OT_add_diamond_collision,
    panels.CollissionPanel
)

def scene_my_collision_material_poll(self, material):
    if bpy.context.scene.PhysicsIdentifier in material.name:
        return material.name


def register():
    from bpy.utils import register_class

    bpy.types.Scene.CollisionMaterials = bpy.props.PointerProperty(
        type=bpy.types.Material,
        poll=scene_my_collision_material_poll
    )

    bpy.types.Scene.PhysicsIdentifier = bpy.props.StringProperty(
        default = "COL",
    )

    for cls in classes:
        register_class(cls)

    # bpy.utils.register_manual_map(add_object_manual_map)
    # bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    # bpy.utils.unregister_manual_map(add_object_manual_map)
    # bpy.types.VIEW3D_MT_mesh_add.remove(add_object_button)


if __name__ == "__main__":
    register()
