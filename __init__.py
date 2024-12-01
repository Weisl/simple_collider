# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(ui)
    importlib.reload(groups)
    importlib.reload(properties)
    importlib.reload(collider_operators)
    importlib.reload(collider_shapes)
    importlib.reload(collider_conversion)
    importlib.reload(auto_Convex)
    importlib.reload(pyshics_materials)
    importlib.reload(rigid_body)
    importlib.reload(presets)
    importlib.reload(preferences)


else:
    from . import ui
    from . import groups
    from . import properties
    from . import collider_operators
    from . import collider_shapes
    from . import collider_conversion
    from . import auto_Convex
    from . import pyshics_materials
    from . import rigid_body
    from . import presets
    from . import preferences

def register():
    # call the register function of the submodules.
    ui.register()

    collider_operators.register()
    collider_shapes.register()
    collider_conversion.register()
    auto_Convex.register()
    pyshics_materials.register()
    rigid_body.register()

    # keymap and preferences should be last
    presets.register()
    preferences.register()
    groups.register()
    properties.register()


def unregister():
    # call unregister function of the submodules.
    preferences.unregister()
    presets.unregister()
    rigid_body.unregister()
    pyshics_materials.unregister()
    auto_Convex.unregister()
    collider_conversion.unregister()
    collider_shapes.unregister()
    collider_operators.unregister()
    properties.unregister()
    groups.unregister()
    ui.unregister()


if __name__ == "__main__":
    register()
