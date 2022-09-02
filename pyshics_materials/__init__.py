import bpy
import bpy.types

from . import material_functions
from . import physics_materials

classes = (
    physics_materials.MATERIAL_OT_physics_material_create,
    physics_materials.MATERIAL_OT_set_physics_material,
    physics_materials.MATERIAL_UL_physics_materials,
)


def get_int(self):
    if self.on_load:
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
        default_mat_name = prefs.physics_material_name

        if not bpy.data.materials.get(default_mat_name):
            mat = material_functions.create_default_material()
            self["material_list_index"] = list(bpy.data.materials).index(mat)
            self['on_load'] = False
            return self["material_list_index"]

    return self["material_list_index"]


def set_int(self, value):
    self["material_list_index"] = value


def register():
    scene = bpy.types.Scene
    material = bpy.types.Material

    scene.on_load = bpy.props.BoolProperty(name='On Load',
                                           default=True)

    scene.material_list_index = bpy.props.IntProperty(name="Index for material list",
                                                      min=0,
                                                      get=get_int,
                                                      set=set_int,
                                                      )

    # register variables saved in the blender scene
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
    del scene.on_load
