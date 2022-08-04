import bpy

from bpy.types import Scene

from . import material_functions
from . import physics_materials

classes = (
    physics_materials.MATERIAL_UL_physics_materials,
)

def getListIndex(self):
    scene = bpy.context.scene
    mat = bpy.data.materials
    if mat is not None:
        idx = scene.objects.find(mat.name)
        return idx
    else:
        return 0



def register():
    Scene.asset_list_index = bpy.props.IntProperty(name = "Index for lis one", default = 0, get = getListIndex)


    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.asset_list_index