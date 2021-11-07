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
    # importlib.reload(physics_materials)
    importlib.reload(vhacd_integration)
    importlib.reload(preferences)

else:
    from . import ui
    from . import operators
    # from . import physics_materials
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
        poll=scene_my_collision_material_poll
    )

    scene.PhysicsIdentifier = bpy.props.StringProperty(
        default="",
        name='Material Filter',
    )

    scene.DefaultMeshMaterial = bpy.props.PointerProperty(
        type=bpy.types.Material,
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

    # call unregister function of the sub-modules
    preferences.unregister()
    vhacd_integration.unregister()
    operators.unregister()
    ui.unregister()
