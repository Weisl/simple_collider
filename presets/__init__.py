import bpy
from bpy.app.handlers import persistent

from . import naming_preset
from . import presets_data
from . import preset_operator


classes = (
    naming_preset.COLLISION_preset,
    preset_operator.SetColliderToolsPreferencesOperator,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)



def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
