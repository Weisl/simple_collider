bl_info = {
    "name": "Collider Tools",
    "description": "Collider Tools is a Blender addon to create physics colliders for games and real-time applications.",
    "author": "Matthias Patscheider",
    "version": (1, 3, 1),
    "blender": (3, 2, 0),
    "location": "View3D > Collider Tools",
    "doc_url": "https://weisl.github.io/collider-tools_overview/",
    "tracker_url": "https://github.com/Weisl/Collider-Tools/issues",
    "category": "Object"}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(ui)
    importlib.reload(groups)
    importlib.reload(collider_operators)
    importlib.reload(collider_shapes)
    importlib.reload(collider_conversion)
    importlib.reload(auto_Convex)
    importlib.reload(pyshics_materials)
    importlib.reload(preferences)


else:
    from . import ui
    from . import groups
    from . import collider_operators
    from . import collider_shapes
    from . import collider_conversion
    from . import auto_Convex
    from . import pyshics_materials
    from . import preferences


def register():
    # call the register function of the sub modules
    ui.register()
    groups.register()
    collider_operators.register()
    collider_shapes.register()
    collider_conversion.register()
    auto_Convex.register()
    pyshics_materials.register()

    # keymap and preferences should be last
    preferences.register()


def unregister():
    # call unregister function of the sub-modules
    preferences.unregister()

    pyshics_materials.unregister()
    auto_Convex.unregister()
    collider_conversion.unregister()
    collider_shapes.unregister()
    collider_operators.unregister()
    groups.unregister()
    ui.unregister()
