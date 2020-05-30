import bmesh
import bpy
from bpy.types import Operator
from bpy_extras.object_utils import object_data_add
from mathutils import Vector

from CollisionHelpers.operators.object_functions import alignObjects, get_bounding_box
from .add_bounding_primitive import OBJECT_OT_add_bounding_object


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


def add_box(context, space):
    """ returns vertex and face information for the bounding box based on the given coordinate space (e.g., world or local)"""

    obj = context.edit_object
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.from_edit_mesh(me)

    selected_verts = [v for v in bm.verts if v.select]
    vertsLoc = []

    # Modify the BMesh, can do anything here...
    positionsX = []
    positionsY = []
    positionsZ = []

    if space == 'GLOBAL':
        # get world space coordinates of the vertices
        for v in selected_verts:
            v_local = v
            v_global = obj.matrix_world @ v_local.co

            positionsX.append(v_global[0])
            positionsY.append(v_global[1])
            positionsZ.append(v_global[2])

    else:
        for v in selected_verts:
            positionsX.append(v.co.x)
            positionsY.append(v.co.y)
            positionsZ.append(v.co.z)

    # get the min and max coordinates for the bounding box
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
    """Create box collider for selected mesh area in edit mode"""

    active_ob = context.object
    root_collection = context.scene.collection

    # add new mesh
    mesh = bpy.data.meshes.new("Box")
    bm = bmesh.new()

    for v_co in verts_loc:
        bm.verts.new(v_co)

    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    # update bmesh to draw properly in viewport
    bm.to_mesh(mesh)
    mesh.update()

    # create new object from mesh and link it to collection
    newCollider = bpy.data.objects.new(active_ob.name + nameSuf, mesh)
    root_collection.objects.link(newCollider)

    if self.my_space == 'LOCAL':
        alignObjects(newCollider, active_ob)

    return newCollider


def box_Collider_from_Objectmode(context, name, obj, i):
    """Create box collider for every selected object in object mode"""
    colliderOb = []

    bBox = get_bounding_box(obj)  # create BoundingBox object for collider
    newCollider = add_box_object(context, bBox, name)

    # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
    # global_bbox_center = obj.matrix_world @ local_bbox_center
    centreBase = sum((Vector(b) for b in obj.bound_box), Vector())
    centreBase /= 8
    # newCollider.matrix_world = centreBase

    alignObjects(newCollider, obj)

    return newCollider


class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box Collision"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        super().invoke(context, event)
        return self.execute(context)

    def execute(self, context):
        nameSuf = self.name_suffix
        matName = self.physics_material_name

        if context.object.mode == "EDIT":
            verts_loc, faces = add_box(context, self.my_space)
            newCollider = box_Collider_from_Editmode(self, context, verts_loc, faces, nameSuf)

            self.set_viewport_drawing(context, newCollider, matName)

        else:
            for i, obj in enumerate(context.selected_objects.copy()):
                newCollider = box_Collider_from_Objectmode(context, nameSuf, obj, i)

                self.set_viewport_drawing(context, newCollider, matName)

        return {'FINISHED'}
