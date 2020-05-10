import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

from .utils import alignObjects, getBoundingBox, setOriginToCenterOfMass, add_displace_mod


def add_box_object(context, vertices, newName):
    """Generate a new object from the given vertices"""
    verts = vertices
    edges = []
    faces = [[0, 1, 2, 3], [7, 6, 5, 4], [5, 6, 2, 1], [0, 3, 7, 4], [3, 2, 6, 7], [4, 5, 1, 0]]

    mesh = bpy.data.meshes.new(name=newName)
    mesh.from_pydata(verts, edges, faces)

    # useful for development when the mesh may be invalid.
    # mesh.validate(verbose=True)
    newObj = object_data_add(context, mesh, operator=None, name=None)  # links to object instance

    return newObj


def add_box(context):
    obj = context.edit_object
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.from_edit_mesh(me)

    selected_verts = [v for v in bm.verts if v.select]
    vertsLoc = []
    vertsLoc = selected_verts

    #    for v in selected_verts:
    #        v_local = Vector((v))
    #        v_global = obj.matrix_world @ v_local
    #        vertsLoc.append(v_global)
    #
    #    for v in selected_verts:
    #        mat = obj.matrix_world
    #        vertsLoc.append(v.transform(mat))

    # Modify the BMesh, can do anything here...
    positionsX = []
    positionsY = []
    positionsZ = []

    for v in vertsLoc:
        positionsX.append(v.co.x)
        positionsY.append(v.co.y)
        positionsZ.append(v.co.z)

    verts = [
        (max(positionsX), max(positionsY), min(positionsZ)),
        (max(positionsX), min(positionsY), min(positionsZ)),
        (min(positionsX), min(positionsY), min(positionsZ)),
        (min(positionsX), max(positionsY), min(positionsZ)),
        (max(positionsX), max(positionsY), max(positionsZ)),
        (max(positionsX), min(positionsY), max(positionsZ)),
        (min(positionsX), min(positionsY), max(positionsZ)),
        (min(positionsX), max(positionsY), max(positionsZ)),
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]

    return verts, faces


def box_Collider_from_Editmode(self, context, verts_loc, faces, nameSuf):
    active_ob = bpy.context.object
    root_col = bpy.context.scene.collection

    mesh = bpy.data.meshes.new("Box")
    bm = bmesh.new()

    for v_co in verts_loc:
        bm.verts.new(v_co)

    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    bm.to_mesh(mesh)
    mesh.update()

    # # add the mesh as an object into the scene with this utility module
    # from bpy_extras import object_utils
    # object_utils.object_data_add(context, mesh, operator=self)
    newCollider = bpy.data.objects.new(active_ob.name + nameSuf, mesh)
    root_col.objects.link(newCollider)
    alignObjects(newCollider, active_ob)

    return newCollider


def box_Collider_from_Objectmode(context, name, obj, i):
    """Create box collider for every selected object in object mode"""
    colliderOb = []

    bBox = getBoundingBox(obj)  # create BoundingBox object for collider
    newCollider = add_box_object(context, bBox, name)

    # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
    # global_bbox_center = obj.matrix_world @ local_bbox_center
    centreBase = sum((Vector(b) for b in obj.bound_box), Vector())
    # print ('CENTRE' + str(centreBase))
    centreBase /= 8
    # print ('CENTRE 2 ' + str(centreBase))
    # newCollider.matrix_world = centreBase

    alignObjects(newCollider, obj)

    return newCollider


def setColliderSettings(self, context, collider):
    collider.display_type = self.my_collision_shading_view
    collider.color = self.my_color
    add_displace_mod(collider, self.my_offset)


class OBJECT_OT_add_box_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_box_collision"
    bl_label = "Add Box Collision"
    bl_options = {'REGISTER', 'UNDO'}

    my_collision_shading_view: EnumProperty(
        name="Axis",
        items=(
            ('SOLID', "SOLID", "SOLID"),
            ('WIRE', "WIRE", "WIRE"),
            ('BOUNDS', "BOUNDS", "BOUNDS"),
        )

    )
    my_offset: FloatProperty(
        name="Offset",
        default=0.0
    )

    my_color: bpy.props.FloatVectorProperty(
        name="Collision Color", description="", default=(0.36, 0.5, 1, 0.25),min=0.0, max=1.0,
        subtype='COLOR', size=4
    )


    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        colSuffix = prefs.colSuffix
        colPreSuffix = prefs.colPreSuffix
        boxColSuffix = prefs.boxColSuffix

        nameSuf = colPreSuffix + boxColSuffix + colSuffix
        if context.object.mode == "EDIT":
            verts_loc, faces = add_box(context)
            newCollider = box_Collider_from_Editmode(self, context, verts_loc, faces, nameSuf)
            setColliderSettings(self, context, newCollider)
        else:
            for i, obj in enumerate(context.selected_objects.copy()):
                newCollider = box_Collider_from_Objectmode(context, nameSuf, obj, i)
                setColliderSettings(self, context, newCollider)

        return {'FINISHED'}


class OBJECT_OT_add_box_per_object_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_box_per_object_collision"
    bl_label = "Add Box Collision Ob"
    bl_options = {'REGISTER', 'UNDO'}

    # scale: FloatVectorProperty(
    #     name="scale",
    #     default=(1.0, 1.0, 1.0),
    #     subtype='TRANSLATION',
    #     description="scaling",
    # )

    def execute(self, context):
        return {'FINISHED'}
