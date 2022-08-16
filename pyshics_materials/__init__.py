import bpy
import bpy.types

from . import material_functions
from . import physics_materials

classes = (
    physics_materials.MATERIAL_OT_physics_material_create,
    physics_materials.MATERIAL_OT_set_physics_material,
    physics_materials.MATERIAL_UL_physics_materials,
)


def register():
    scene = bpy.types.Scene
    material = bpy.types.Material

    scene.material_list_index = bpy.props.IntProperty(name="Index for material list", default=0)

    # register variables saved in the blender scene¶

    scene.DefaultMeshMaterial = bpy.props.PointerProperty(
        type=bpy.types.Material,
        name='Default Mesh Material',
        description='The default mesh material will be assigned to any mesh that is converted from a collider to a mesh object'
    )

    material.edit = bpy.props.BoolProperty(name="Manipulate", default=False)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    scene = bpy.types.Scene
    material = bpy.types.Material

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete variables saved in the scenes file
    del material.edit
    del scene.DefaultMeshMaterial
    del scene.material_list_index
