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


def alignObjects(new, old):
    """Align two objects"""
    new.matrix_world = old.matrix_world


def getBoundingBox(obj):
    return obj.bound_box


def setOriginToCenterOfMass(ob):
    """"""
    oldActive = bpy.context.object
    bpy.context.view_layer.objects.active = ob

    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    bpy.context.view_layer.objects.active = oldActive

def removeMaterials(obj):
    if obj.type == 'MESH' or obj.type == 'CURVE' or obj.type == 'SURFACE' or obj.type == 'FONT' or obj.type == 'META':
        for i in range(0, len(obj.material_slots)):
            obj.active_material_index = i
            bpy.ops.object.material_slot_remove()
            #print ("entered")

def setMaterial(ob, mat):
    '''Assign material to object'''
    # add material to object
    me = ob.data
    me.materials.append(mat)


def add_displace_mod(ob, strenght):
    # add inflate modifier
    mod = ob.modifiers.new(name="ColliderOffset_disp", type='DISPLACE')
    mod.strength = strenght

def setColliderSettings(self, context, collider, matname):
    collider.display_type = self.my_collision_shading_view
    collider.color = self.my_color
    add_displace_mod(collider, self.my_offset)
    removeMaterials(collider)
    setMaterial(collider, matname)

