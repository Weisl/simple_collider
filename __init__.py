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


def register():
    # call the register function of the sub modules
    ui.register()
    operators.register()
    auto_Convex.register()
    pyshics_materials.register()

    # keymap and preferences should be last
    preferences.register()


def unregister():
    # call unregister function of the sub-modules
    preferences.unregister()
    pyshics_materials.unregister()
    auto_Convex.unregister()
    operators.unregister()
    ui.unregister()
