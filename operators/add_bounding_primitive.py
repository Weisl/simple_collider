from bpy.props import (
    EnumProperty,
    FloatProperty,
    FloatVectorProperty
)

from .object_functions import add_displace_mod
from ..pyshics_materials.material_functions import remove_materials, set_material


class OBJECT_OT_add_bounding_object():
    """Abstract parent class to contain common methods and properties for all add bounding object operators"""
    bl_options = {'REGISTER', 'UNDO'}

    # Display setting of the bounding object in the viewport
    my_collision_shading_view: EnumProperty(
        name="Shading",
        items=(
            ('SOLID', "SOLID", "SOLID"),
            ('WIRE', "WIRE", "WIRE"),
            ('BOUNDS', "BOUNDS", "BOUNDS"),
        )
    )

    # Tranformation space to be used for creating the bounding object.
    my_space: EnumProperty(
        name="Axis",
        items=(
            ('LOCAL', "LOCAL", "LOCAL"),
            ('GLOBAL', "GLOBAL", "GLOBAL")),
        default="LOCAL"
    )

    # The offset used in a displacement modifier on the bounding object to
    # either push the bounding object inwards or outwards
    my_offset: FloatProperty(
        name="Bounding Surface Offset",
        default=0.0
    )

    # The object color for the bounding object
    my_color: FloatVectorProperty(
        name="Bounding Object Color", description="", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    def set_viewport_drawing(self, context, bounding_object, physics_material_name):
        ''' Assign material to the bounding object and visibility settings.'''
        bounding_object.display_type = self.my_collision_shading_view
        bounding_object.color = self.my_color
        add_displace_mod(bounding_object, self.my_offset)
        remove_materials(bounding_object)
        set_material(bounding_object, physics_material_name)

    def invoke(self, context, event):
        # get collision suffix from preferences
        prefs = context.preferences.addons['CollisionHelpers'].preferences
        colSuffix = prefs.colSuffix
        colPreSuffix = prefs.colPreSuffix
        boxColSuffix = prefs.boxColSuffix
        self.name_suffix = colPreSuffix + boxColSuffix + colSuffix

        # get physics material from properties panel
        scene = context.scene
        self.physics_material_name = scene.CollisionMaterials

