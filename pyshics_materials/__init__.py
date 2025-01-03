import bpy
import bpy.types

from . import material_functions
from . import material_list
from . import physics_materials

classes = (
    material_list.BUTTON_OP_set_active_physics_material,
    material_list.MATERIAL_UL_physics_materials,
    physics_materials.MATERIAL_OT_physics_material_create,
    physics_materials.MATERIAL_OT_set_physics_material,
    physics_materials.MATERIAL_OT_physics_material_random_color,
)


def register():
    scene = bpy.types.Scene
    scene.use_physics_tag = bpy.props.BoolProperty(name="Filter", default=False)
    materialType = bpy.types.Material

    scene.active_physics_material = bpy.props.PointerProperty(name="My Node", type=materialType)

    materialType.edit = bpy.props.BoolProperty(name="Manipulate", default=False)
    materialType.isPhysicsMaterial = bpy.props.BoolProperty(name="Is Physics Material", default=False)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    materialType = bpy.types.Material

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete variables saved in the scenes file
    del materialType.edit
