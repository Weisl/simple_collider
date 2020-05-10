import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

from .utils import alignObjects, getBoundingBox, setOriginToCenterOfMass


class CollissionPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Collision"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pipeline"

    def draw(self, context):
        layout = self.layout

        obj = context.object

        row = layout.row()
        row.operator("mesh.add_box_collision")
        row = layout.row()
        row.operator("mesh.add_diamond_collision")

        row = layout.row()
        row.operator("mesh.add_cylinder_per_object_collision")
        # row = layout.row()
        # row.operator("mesh.add_box_per_object_collision")
