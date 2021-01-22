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


def generate_box(positionsX, positionsY, positionsZ):
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


def verts_faces_to_bbox_collider(self, context, verts_loc, faces, nameSuf):
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
    print("active_ob.name = " + active_ob.name)
    newCollider = bpy.data.objects.new(active_ob.name + nameSuf, mesh)

    root_collection.objects.link(newCollider)

    scene = context.scene
    if scene.my_space == 'LOCAL':
        newCollider.parent = active_ob
        alignObjects(newCollider, active_ob)
    else:
        bpy.ops.object.mode_set(mode='OBJECT')
        self.custom_set_parent(context, active_ob, newCollider)
        bpy.ops.object.mode_set(mode='EDIT')

    return newCollider


def box_Collider_from_Objectmode(self, context, name, obj, i):
    """Create box collider for every selected object in object mode"""
    colliderOb = []

    scene = context.scene

    if scene.my_space == 'LOCAL':
        # create BoundingBox object for collider
        bBox = get_bounding_box(obj)
        newCollider = add_box_object(context, bBox, name)

        # set parent
        newCollider.parent = obj

        # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
        # global_bbox_center = obj.matrix_world @ local_bbox_center
        centreBase = sum((Vector(b) for b in obj.bound_box), Vector())
        centreBase /= 8

        # newCollider.matrix_world = centreBase
        alignObjects(newCollider, obj)

    # Space == 'Global'
    else:
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        used_vertices = self.get_vertices(obj, mode='OBJECT')
        positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
        verts_loc, faces = generate_box(positionsX, positionsY, positionsZ)
        newCollider = verts_faces_to_bbox_collider(self, context, verts_loc, faces, name)

        bpy.ops.object.mode_set(mode='OBJECT')

        self.custom_set_parent(context, obj, newCollider)

    return newCollider


class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box Collision"

    def invoke(self, context, event):
        super().invoke(context, event)
        # return self.execute(context)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        scene = context.scene

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            scene.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            scene.my_space = 'LOCAL'
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        nameSuf = self.name_suffix
        matName = self.physics_material_name

        scene = context.scene

        self.remove_objects(self.previous_objects)
        self.previous_objects = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)

        # Create the bounding geometry, depending on edit or object mode.
        for i, obj in enumerate(self.selected_objects):

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            context.view_layer.objects.active = obj
            collections = obj.users_collection

            if obj.mode == "EDIT":
                me = context.edit_object.data
                if self.bm is None or not self.bm.is_valid:
                    # in edit mode so try make a new bmesh
                    self.set_bmesh(context)

                used_vertices = self.get_vertices(obj, preselect_all=False)
                positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
                verts_loc, faces = generate_box(positionsX, positionsY, positionsZ)
                new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, faces, obj.mode + nameSuf)

                # save collision objects to delete when canceling the operation
                self.previous_objects.append(new_collider)
                self.cleanup(context, new_collider, matName)
                self.add_to_collections(new_collider, collections)

            else:  # mode == "OBJECT":

                new_collider = box_Collider_from_Objectmode(self, context, nameSuf, obj, i)

                # save collision objects to delete when canceling the operation
                self.previous_objects.append(new_collider)
                self.cleanup(context, new_collider, matName)
                self.add_to_collections(new_collider, collections)

        return {'RUNNING_MODAL'}
