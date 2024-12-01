from . import naming_preset
from . import presets_data
from . import preset_operator
from . import convert_old_presets

classes = (
    naming_preset.COLLISION_preset,
    naming_preset.PRESET_OT_load_preset,
    preset_operator.SetColliderToolsPreferencesOperator,
    convert_old_presets.UpgradeColliderToolsPresetsOperator
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)



def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
