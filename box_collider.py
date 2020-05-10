import bmesh
import bpy
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

from .utils import alignObjects, getBoundingBox, setOriginToCenterOfMass


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


def box_Collider_from_Editmode(self, context, verts_loc, faces):
    prefs = bpy.context.preferences.addons[__package__].preferences
    colSuffix = prefs.colSuffix
    colPreSuffix = prefs.colPreSuffix
    boxColSuffix = prefs.boxColSuffix

    active_ob = bpy.context.object
    #        verts_loc, faces = add_box()
    root_col = bpy.context.scene.collection

    name = active_ob.name + colPreSuffix + boxColSuffix + colSuffix
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
    obj = bpy.data.objects.new("Obj", mesh)
    root_col.objects.link(obj)
    alignObjects(obj, active_ob)


def box_Collider_from_Objectmode(context):
    """Create box collider for every selected object in object mode"""
    prefs = bpy.context.preferences.addons[__package__].preferences
    colSuffix = prefs.colSuffix
    colPreSuffix = prefs.colPreSuffix
    boxColSuffix = prefs.boxColSuffix

    active_ob = bpy.context.active_object
    selectedObjects = bpy.context.selected_objects.copy()
    colliderOb = []

    for i, obj in enumerate(selectedObjects):
        bBox = getBoundingBox(obj)  # create BoundingBox object for collider
        newCollider = add_box_object(context, bBox, obj.name + colPreSuffix + boxColSuffix + colSuffix)

        # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
        # global_bbox_center = obj.matrix_world @ local_bbox_center
        # centre =  sum((Vector(b) for b in obj.bound_box), Vector())
        # print ('CENTRE' + str(centre))
        # centre /= 8
        # print ('CENTRE 2 ' + str(centre))
        # newCollider.matrix_world = obj.matrix_world * (1 / 8 *

        alignObjects(newCollider, obj)


class OBJECT_OT_add_box_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_box_collision"
    bl_label = "Add Box Collision"
    bl_options = {'REGISTER', 'UNDO'}

    scale: FloatVectorProperty()

    def execute(self, context):
        if context.object.mode == "EDIT":
            verts_loc, faces = add_box(context)
            box_Collider_from_Editmode(self, context, verts_loc, faces)
        else:
            box_Collider_from_Objectmode(context)
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
