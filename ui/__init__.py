import os
import shutil
from pathlib import Path

from . import properties_panels
from .properties_panels import collider_presets_folder

classes = (
    properties_panels.EXPLORER_OT_open_folder,
    properties_panels.PREFERENCES_OT_open_addon,
    properties_panels.OBJECT_MT_collision_presets,
    properties_panels.VIEW3D_MT_collision,
    properties_panels.VIEW3D_MT_collision_visibility,
    properties_panels.VIEW3D_MT_collision_physics_materials,
    properties_panels.VIEW3D_PT_collission_panel,
    properties_panels.VIEW3D_PT_collission_visibility_panel,

    # properties_panels.VIEW3D_PT_collission_settings_panel,
    properties_panels.VIEW3D_PT_collission_material_panel,
    properties_panels.VIEW3D_MT_PIE_template,
)


def get_preset_folder_path():
    path = Path(str(__file__))
    parent = path.parent.parent.parent.absolute()

    collider_presets = "collider_tools"
    collider_addon_directory = os.path.join(parent, collider_presets, "presets")

    return collider_addon_directory


def initialize_presets():
    my_presets = collider_presets_folder()
    print('my_presets ' + my_presets)

    # Get a list of all the files in your bundled presets folder
    my_bundled_presets = get_preset_folder_path()
    print('my_bundled_presets ' + str(my_bundled_presets))
    files = os.listdir(my_bundled_presets)
    print('list my_bundled_presets ' + str(my_bundled_presets))

    # if not os.path.isdir(my_presets):
    #     # makedirs() will also create all the parent folders (like "object")
    #     try:
    #         os.makedirs(my_presets)
    #     except:
    #         pass

    # Copy them
    for f in files:
        filepath = os.path.join(my_bundled_presets, f)
        print('FILEPATH = ' + filepath)
        shutil.copy2(filepath, my_presets)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    # addon_name = str(__package__.split('.')[0])
    # print("FILE = " + str(__file__))
    # print("PACKAGE = " + str(__package__))
    # print("NAME = " + str(__name__))

    initialize_presets()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
