bl_info = {
    "name": "CollisionHelpers",
    "description": "",
    "author": "Matthias Patscheider",
    "version": (0, 5, 0),
    "blender": (2, 93, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "https://github.com/Weisl/CollisionHelpers",
    "tracker_url": "https://github.com/Weisl/CollisionHelpers/issues",
    "category": "Object"}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(ui)
    importlib.reload(operators)
    importlib.reload(vhacd_integration)
    importlib.reload(preferences)

else:
    from . import ui
    from . import operators
    from . import vhacd_integration
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
        description='Physical Materials are used in game enginges to define different responses of a physical object when interacting with other elements of the game world. They can be used to trigger different audio, VFX or gameplay events depending on the material.'
    )

    scene.PhysicsIdentifier = bpy.props.StringProperty(
        default="",
        description="Filter physics materials out based on their naming.",
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
    vhacd_integration.register()

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
    vhacd_integration.unregister()
    operators.unregister()
    ui.unregister()
