from multiprocessing import context
import bpy
import os
import platform
from bpy.app.handlers import persistent
from pathlib import Path
from tempfile import gettempdir

from .keymap import keymaps_items_dict
from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..groups.user_groups import set_default_group_values
from ..presets.naming_preset import COLLISION_preset
from ..presets.preset_operator import SetSimpleColliderPreferencesOperator
from ..presets.presets_data import presets
from ..pyshics_materials.material_functions import set_default_active_mat
from ..ui.properties_panels import OBJECT_MT_collision_presets
from ..ui.properties_panels import VIEW3D_PT_collision_material_panel
from ..ui.properties_panels import VIEW3D_PT_collision_panel
from ..ui.properties_panels import VIEW3D_PT_collision_settings_panel
from ..ui.properties_panels import VIEW3D_PT_collision_visibility_panel
from ..ui.properties_panels import label_multiline
from ..ui.properties_panels import collider_presets_folder

collection_colors = [
    ("NONE", "White", "Default collection color", "OUTLINER_COLLECTION", 0),
    ("COLOR_01", "Red", "Red collection color", "COLLECTION_COLOR_01", 1),
    ("COLOR_02", "Orange", "Orange collection color", "COLLECTION_COLOR_02", 2),
    ("COLOR_03", "Yellow", "Yellow collection color", "COLLECTION_COLOR_03", 3),
    ("COLOR_04", "Green", "Green collection color", "COLLECTION_COLOR_04", 4),
    ("COLOR_05", "Blue", "Blue collection color", "COLLECTION_COLOR_05", 5),
    ("COLOR_06", "Violet", "Violet collection color", "COLLECTION_COLOR_06", 6),
    ("COLOR_07", "Pink", "Pink collection color", "COLLECTION_COLOR_07", 7),
    ("COLOR_08", "Brown", "Brown collection color", "COLLECTION_COLOR_08", 8),
]


def setDefaultTemp():
    """
    Set the default temporary directory for the simple collider addon.
    Returns the system's temp directory as a fallback.
    """
    import tempfile
    return tempfile.gettempdir()  # Always returns the system temp directory


def update_panel_category(self, context):
    """Update panel tab for collider tools"""
    panels = [
        VIEW3D_PT_collision_panel,
        VIEW3D_PT_collision_settings_panel,
        VIEW3D_PT_collision_visibility_panel,
        VIEW3D_PT_collision_material_panel,
    ]

    for panel in panels:
        try:
            bpy.utils.unregister_class(panel)
        except:
            pass

        panel.bl_category = context.preferences.addons[base_package].preferences.collider_category
        bpy.utils.register_class(panel)
    return


def get_default_executable_path():
    """Set the default executable path for the vhacd executable to the addon folder. """
    path = Path(str(__file__))
    parent = path.parent.parent.absolute()

    vhacd_app_folder = "v-hacd_app"

    if platform.system() not in ['Windows', 'Linux']:
        return ''

    OS_folder = ''
    app_name = ''

    if platform.system() == 'Windows':
        OS_folder = 'Win'
        app_name = 'vhacd_4_1_win_amd64.exe'
    elif platform.system() == 'Linux':
        OS_folder = 'Linux'
        app_name = 'vhacd_4_1_linux_amd64'

    collider_addon_directory = os.path.join(
        parent, vhacd_app_folder, OS_folder)

    if os.path.isdir(collider_addon_directory):
        executable_path = os.path.join(collider_addon_directory, app_name)
        if os.path.isfile(executable_path):
            return executable_path

    # if folder or file does not exist, return empty string
    return ''


def update_keymap(self, context, keymap_name):
    wm = context.window_manager
    addon_km = wm.keyconfigs.addon.keymaps.get("Window") # Using Window instead of 3D View to fix issue of keymap not working on Linux
    if not addon_km:
        return

    from .keymap import keymaps_items_dict
    item = keymaps_items_dict[keymap_name]
    name = item["name"]
    idname = item["idname"]
    operator = item["operator"]

    # Get current values from preferences
    key_type = getattr(self, f"{name}_type").upper()
    ctrl = getattr(self, f"{name}_ctrl")
    shift = getattr(self, f"{name}_shift")
    alt = getattr(self, f"{name}_alt")
    active = getattr(self, f"{name}_active")  # Get the active state from preferences

    # Remove existing keymap items for this operator
    for kmi in addon_km.keymap_items[:]:
        if kmi.idname == idname and hasattr(kmi.properties, 'name') and kmi.properties.name == operator:
            addon_km.keymap_items.remove(kmi)

    # Add new keymap item if type is not 'NONE'
    if key_type != 'NONE':
        kmi = addon_km.keymap_items.new(
            idname=idname,
            type=key_type,
            value='PRESS',
            ctrl=ctrl,
            shift=shift,
            alt=alt,
        )
        kmi.properties.name = operator
        kmi.active = active  # Set the active state from preferences
    else:
        # If type is 'NONE', ensure no keymap item exists
        pass

    wm.keyconfigs.update()  # Refresh keymaps to apply changes

from .prefs_properties import CollisionAddonPrefsProperties
class CollisionAddonPrefs(bpy.types.AddonPreferences, CollisionAddonPrefsProperties):
    """Addon preferences for Simple Collider"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    # Has to be named like the main addon folder
    # __package__ works on multi file and __name__ not
    bl_idname = base_package
    bl_options = {'REGISTER'}


    def draw_settings_panel(self, layout):
        """Draw the settings panel"""
        box = layout.box()
        row = box.row()
        row.label(text='General')
        for propName in self.general_props:
            row = box.row()
            row.prop(self, propName)

        box = layout.box()
        row = box.row()
        row.label(text='Collections')
        for propName in self.col_props:
            row = box.row()
            row.prop(self, propName)

        box = layout.box()
        row = box.row(align=True)
        row.label(text="Collider Display")
        for propName in self.display_config:
            row = box.row()
            row.prop(self, propName)

        row = layout.row()
        row.prop(self, 'debug')

    def draw_naming_panel(self, layout):
        """Draw the naming panel"""
        box = layout.box()
        row = box.row()
        row.label(text="Default Presets")
        row = box.row(align=True)
        for preset_name in presets.keys():
            op = row.operator(SetSimpleColliderPreferencesOperator.bl_idname, text=f"{preset_name}")
            op.preset_name = preset_name
        row = box.row(align=True)
        row.label(text="User Presets")
        row = box.row(align=True)
        op = row.operator('object.upgrade_simple_collider_presets')
        row = box.row(align=True)
        row.menu('OBJECT_MT_collision_presets', text=OBJECT_MT_collision_presets.bl_label)
        row.operator(COLLISION_preset.bl_idname, text="", icon='ADD')
        row.operator(COLLISION_preset.bl_idname, text="", icon='REMOVE').remove_active = True
        row.operator("wm.url_open", text="", icon='HELP').url = "https://weisl.github.io/collider_import_engines/"

        row.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = collider_presets_folder()

        box_name = box.box()
        row = box.row()
        row.prop(self, "naming_position", expand=True)

        row = box_name.row()
        if self.naming_position == 'PREFIX':
            row.label(text="Name = Collider Prefix + Shape + Group + Collider Suffix + Basename + Numbering")
        else:
            row.label(text="Name = Basename + Collider Prefix + Shape + Group + Collider Suffix + Numbering")

        row = box_name.row()
        row.label(text="E.g. " + OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier='box_shape',
                                                                                   user_group='USER_01',
                                                                                   basename='Suzanne'))

        row = box.row()
        row.prop(self, "replace_name")
        row = box.row()
        if not self.replace_name:
            row.enabled = False
        row.prop(self, "obj_basename")

        for propName in self.props:
            row = box.row()
            row.prop(self, propName)

        box2 = layout.box()
        box2.label(text="Shape")
        for propName in self.props_shapes:
            row = box2.row()
            row.prop(self, propName)

        box = layout.box()
        box.label(text="Rigid Body")
        for propName in self.props_parent:
            row = box.row()
            row.prop(self, propName)

        box = layout.box()
        box.label(text="Collider Groups")
        for propName in self.props_collider_groups:
            row = box.row()
            row.prop(self, propName)

        col = box.column()
        if not self.collider_groups_enabled:
            col.enabled = False

        for count, (prop_01, prop_02) in enumerate(
                zip(self.props_collider_groups_name, self.props_collider_groups_identifier), start=1):
            split = col.split(align=True, factor=0.1)
            split.label(text=f"Group_{str(count)}:")
            split = split.split(align=True, factor=0.5)
            split.prop(self, prop_01)
            split.prop(self, prop_02)

        box = layout.box()
        box.label(text="Physics Materials")
        for propName in self.props_physics_materials:
            row = box.row()
            row.prop(self, propName)

        box = box.box()
        row = box.row()
        row.prop(self, "use_physics_material")
        row = box.row()
        row.prop(self, "skip_material")

        col = box.column()
        if not self.use_physics_material:
            col.enabled = False

        row = col.row()
        row.prop(self, "material_naming_position", expand=True)
        for propName in self.props_advanced_physics_materials:
            row = col.row()
            row.prop(self, propName)

    def draw_keymap_panel(self, layout):
        """Draw the keymap panel"""
        for key, value in keymaps_items_dict.items():
            self.keymap_ui(layout, key, value['name'], value['idname'], value['operator'])

    def draw_ui_panel(self, layout):
        """Draw the UI panel"""
        row = layout.row()
        row.prop(self, "collider_category", expand=True)

        layout.separator()
        row = layout.row()
        row.label(text="3D Viewport Colors")

        for propName in self.ui_col_colors:
            row = layout.row()
            row.prop(self, propName)

        row = layout.row()
        row.label(text="UI Settings")

        for propName in self.ui_props:
            row = layout.row()
            row.prop(self, propName)

    def draw_vhacd_panel(self, layout, context):

        box = layout.box()
        box.label(text="Platform Support", icon='INFO')

        if platform.system() == 'Windows':
            box.label(text="Supported (Windows 10/11)")

        elif platform.system() == 'Linux':
            box.label(text="Supported (Linux Mint/Ubuntu).")
            box.label(text="You can also use a custom build of vhacd compiled for your Linux distribution.")
            
            # Info about execute permissions
            row = box.row()
            row.label(text="Make sure to give execute permissions to the vhacd executable")
            row.operator("wm.url_open", text="How to guide", icon='HELP').url = "https://weisl.github.io"
        
        else:
            box.label(text="Auto Conevx is currently not supported on MacOS", icon='ERROR')



        box = layout.box()
        box.label(text="Executable Paths", icon='FILE_FOLDER')
        row = box.row()
        row.enabled = False
        row.label(text="Default Executable:")
        row.prop(self, 'default_executable_path', text="")
        
        row = box.row()
        row.label(text="Custom Executable (Optional):")
        row.prop(self, 'executable_path', text="")

        box = layout.box()
        box.label(text="Temporary Data", icon='FILE_FOLDER')
        box.label(text="Directory used to store temporary vhacd files during convex hull generation.")
        row = box.row()
        if not self.data_path:
            row.alert = True
        row.prop(self, "data_path", icon='ERROR' if not self.data_path else 'FILE_FOLDER')

        if self.executable_path or self.default_executable_path:
            box = layout.box()
            box.label(text="VHACD Settings", icon='SETTINGS')
            for propName in self.vhacd_props_config:
                row = box.row()
                row.prop(self, propName)
                row.operator("wm.url_open", text="", icon='QUESTION').url = f"https://github.com/kmammou/v-hacd#{propName}"

    def draw_support_panel(self, layout, context):
        """Draw the support panel"""
        box = layout.box()

        col = box.column(align=True)
        row = col.row()
        row.label(text="♥♥♥ Leave a Review or Rating! ♥♥♥")
        row = col.row()
        row.label(text='Support & Feedback')
        row = col.row(align=True)
        row.label(text="Simple Collider")
        row.operator("wm.url_open", text="Superhive", icon="URL").url = "https://superhivemarket.com/products/simple-collider"
        row.operator("wm.url_open", text="Gumroad", icon="URL").url = "https://weisl.gumroad.com/l/simple_collider"

        col = box.column(align=True)
        row = col.row()
        row.label(text='Join the Discussion!')
        row = col.row()
        row.operator("wm.url_open", text="Join Discord", icon="URL").url = "https://discord.gg/VRzdcFpczm"

        box = layout.box()
        col = box.column(align=True)
        text = "Explore my other Blender Addons designed for more efficient game asset workflows!"
        label_multiline(context=context, text=text, parent=col)

        box.label(text="Simple Tools ($)")
        col = box.column(align=True)

        row = col.row(align=True)
        row.label(text="Simple Camera Manager")
        row.operator("wm.url_open", text="Superhive", icon="URL").url = "https://superhivemarket.com/products/simple-camera-manager"
        row.operator("wm.url_open", text="Gumroad", icon="URL").url = "https://weisl.gumroad.com/l/simple_camera_manager"

        row = col.row(align=True)
        row.label(text="Simple Export")
        row.operator("wm.url_open", text="Gumroad", icon="URL").url = "https://weisl.gumroad.com/l/simple_export"

        box.label(text="Simple Tools (Free)")
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Simple Renaming")
        row.operator("wm.url_open", text="Blender Extensions", icon="URL").url = "https://extensions.blender.org/add-ons/simple-renaming-panel/"
        row.operator("wm.url_open", text="Gumroad", icon="URL").url = "https://weisl.gumroad.com/l/simple_renaming"

    def keymap_ui(self, layout, title, property_prefix, id_name, properties_name):
        box = layout.box()
        split = box.split(align=True, factor=0.5)
        col = split.column()

        # Is hotkey active checkbox
        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_active', text="")
        row.label(text=title)

        # Button to assign the key assignments
        col = split.column()
        row = col.row(align=True)
        key_type = getattr(self, f'{property_prefix}_type')
        text = (
            bpy.types.Event.bl_rna.properties['type'].enum_items[key_type].name
            if key_type != 'NONE'
            else 'Press a key'
        )

        op = row.operator("collision.key_selection_button", text=text)
        op.property_prefix = property_prefix

        # row.prop(self, f'{property_prefix}_type', text="")
        op = row.operator("collision.remove_hotkey", text="", icon="X")
        op.idname = id_name
        op.properties_name = properties_name
        op.property_prefix = property_prefix

        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_ctrl')
        row.prop(self, f'{property_prefix}_shift')
        row.prop(self, f'{property_prefix}_alt')

    # here you specify how they are drawn
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':
            self.draw_settings_panel(layout)

        elif self.prefs_tabs == 'NAMING':
            self.draw_naming_panel(layout)

        elif self.prefs_tabs == 'VHACD':
            self.draw_vhacd_panel(layout, context)

        elif self.prefs_tabs == 'KEYMAP':
            self.draw_keymap_panel(layout)

        elif self.prefs_tabs == 'UI':
            self.draw_ui_panel(layout)

        elif self.prefs_tabs == 'SUPPORT':
            self.draw_support_panel(layout, context)

classes = (
    CollisionAddonPrefs,
)


@persistent
def _load_handler(dummy):
    """
    Handler function that is called when a new Blender file is loaded.
    This function sets the default active material and default group values.
    """
    set_default_active_mat()
    set_default_group_values()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_panel_category(None, bpy.context)

    # Append the load handler to be executed after loading a Blender file
    bpy.app.handlers.load_post.append(_load_handler)


def unregister():
    from bpy.utils import unregister_class
    from ..ui.properties_panels import collider_presets_folder
    from .keymap import keymaps_items_dict

    for cls in reversed(classes):
        unregister_class(cls)

    # Remove the load handler
    bpy.app.handlers.load_post.remove(_load_handler)
