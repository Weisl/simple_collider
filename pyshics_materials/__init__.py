import bpy
import bpy.types

from . import material_functions
from . import physics_materials
from . import material_list

classes = (
    material_list.BUTTON_OP_set_active_physics_material,
    material_list.MATERIAL_UL_physics_materials,
    physics_materials.MATERIAL_OT_physics_material_create,
    physics_materials.MATERIAL_OT_set_physics_material,
    physics_materials.MATERIAL_OT_physics_material_random_color,
)


def register():
    scene = bpy.types.Scene
    scene.use_physics_tag = bpy.props.BoolProperty(name="Physics Materials Tag", default=True)
    scene.active_physics_material = bpy.props.StringProperty(name="Active Physics Material", default="")

    material = bpy.types.Material
    material.edit = bpy.props.BoolProperty(name="Manipulate", default=False)
    material.isPhysicsMaterial = bpy.props.BoolProperty(name="Is Physics Material", default=False)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    wm = bpy.types.WindowManager
    material = bpy.types.Material

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete variables saved in the scenes file
    del material.edit
