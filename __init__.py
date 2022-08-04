bl_info = {
    "name": "Collider Tools",
    "description": "Collider Tools is a Blender addon to create physics colliders for games and real-time applications.",
    "author": "Matthias Patscheider",
    "version": (1, 1, 0),
    "blender": (3, 2, 0),
    "location": "View3D > Collider Tools",
    "doc_url": "https://weisl.github.io/collider-tools_overview/",
    "tracker_url": "https://github.com/Weisl/Collider-Tools/issues",
    "category": "Object"}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(ui)
    importlib.reload(operators)
    importlib.reload(auto_Convex)
    importlib.reload(pyshics_materials)
    importlib.reload(preferences)


else:
    from . import ui
    from . import operators
    from . import auto_Convex
    from . import pyshics_materials
    from . import preferences

import bpy

def scene_my_collision_material_poll(self, material):
    ''' Returns material only if the name contains the physics material identifier specified in the preferences '''
    if bpy.context.scene.PhysicsIdentifier in material.name:
        return material.name


def register():
    # register variables saved in the blender scene
    scene = bpy.types.Scene

    scene.CollisionMaterials = bpy.props.PointerProperty(
        type=bpy.types.Material,
        poll=scene_my_collision_material_poll,
        name='Physics Material',
        description='Physical Materials are used in game enginges to define different responses of a physical object when interacting with other elements of the game world. They can be used to trigger different audio, VFX or gameplay events depending on the material. Collider Tools will create a simple semi transparent material called "COL_DEFAULT" if no material is assigned.'
    )

    scene.PhysicsIdentifier = bpy.props.StringProperty(
        default="*COL",
        description='By default, the Physics Material input shows all materials of the blender scene. Use the filter to only display materials that contain the filter characters in their name. E.g.,  Using the filter "COL", all materials that do not have "COL" in their name will be hidden from the physics material selection.',
        name='Physics Material Filter',
    )

    scene.DefaultMeshMaterial = bpy.props.PointerProperty(
        type=bpy.types.Material,
        name = 'Default Mesh Material',
        description='The default mesh material will be assigned to any mesh that is converted from a collider to a mesh object'
    )

    # call the register function of the sub modules
    ui.register()
    operators.register()
    auto_Convex.register()
    pyshics_materials.register()

    # keymap and preferences should be last
    preferences.register()


def unregister():
    scene = bpy.types.Scene

    # delete variables saved in the scenes file
    del scene.CollisionMaterials
    del scene.PhysicsIdentifier
    del scene.DefaultMeshMaterial

    # call unregister function of the sub-modules
    preferences.unregister()
    pyshics_materials.unregister()
    auto_Convex.unregister()
    operators.unregister()
    ui.unregister()
