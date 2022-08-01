import bmesh
import bpy
import math

import numpy as np

from mathutils import Matrix
from ..operators.object_pivot_and_ailgn import alignObjects
from bpy.types import Operator
from .add_bounding_primitive import OBJECT_OT_add_bounding_object


DEBUG = False

CUBE_FACE_INDICES = (
    (0, 1, 3, 2),
    (2, 3, 7, 6),
    (6, 7, 5, 4),
    (4, 5, 1, 0),
    (2, 6, 4, 0),
    (7, 3, 1, 5),
)

class OBJECT_OT_add_aligned_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding box collisions based on the selection"""
    bl_idname = "mesh.add_aligned_bounding_box"
    bl_label = "Add Aligned Box Collision"
    bl_description = 'Create bounding box collisions based on the selection'

    def gen_cube_verts(self):
        for x in range(-1, 2, 2):
            for y in range(-1, 2, 2):
                for z in range(-1, 2, 2):
                    yield x, y, z

    def rotating_calipers(self, hull_points: np.ndarray, bases):
        min_bb_basis = None
        min_bb_min = None
        min_bb_max = None
        min_vol = math.inf
        for basis in bases:
            rot_points = hull_points.dot(np.linalg.inv(basis))
            # Equivalent to: rot_points = hull_points.dot(np.linalg.inv(np.transpose(basis)).T)

            bb_min = rot_points.min(axis=0)
            bb_max = rot_points.max(axis=0)
            volume = (bb_max - bb_min).prod()
            if volume < min_vol:
                min_bb_basis = basis
                min_vol = volume

                min_bb_min = bb_min
                min_bb_max = bb_max

        return np.array(min_bb_basis), min_bb_max, min_bb_min

    def obj_rotating_calipers(self, obj):
        bm = bmesh.new()
        dg = bpy.context.evaluated_depsgraph_get()
        bm.from_object(obj, dg)

        chull_out = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        chull_geom = chull_out["geom"]
        chull_points = np.array([bmelem.co for bmelem in chull_geom if isinstance(bmelem, bmesh.types.BMVert)])

        # Create object from Convex-Hull (for debugging)
        if DEBUG:

            for face in set(bm.faces) - set(chull_geom):
                bm.faces.remove(face)
            for edge in set(bm.edges) - set(chull_geom):
                bm.edges.remove(edge)

            chull_mesh = bpy.data.meshes.new(obj.name + "_convex_hull")
            chull_mesh.validate()
            bm.to_mesh(chull_mesh)
            chull_obj = bpy.data.objects.new(chull_mesh.name, chull_mesh)
            chull_obj.matrix_world = obj.matrix_world
            bpy.context.scene.collection.objects.link(chull_obj)

        bases = []

        for elem in chull_geom:
            if not isinstance(elem, bmesh.types.BMFace):
                continue
            if len(elem.verts) != 3:
                continue

            face_normal = elem.normal
            if np.allclose(face_normal, 0, atol=0.00001):
                continue

            for e in elem.edges:
                v0, v1 = e.verts
                edge_vec = (v0.co - v1.co).normalized()
                co_tangent = face_normal.cross(edge_vec)
                basis = (edge_vec, co_tangent, face_normal)
                bases.append(basis)

        bb_basis, bb_max, bb_min = self.rotating_calipers(chull_points, bases)

        bm.free()

        bb_basis_mat = bb_basis.T

        bb_dim = bb_max - bb_min
        bb_center = (bb_max + bb_min) / 2

        mat = Matrix.Translation(bb_center.dot(bb_basis)) @ Matrix(bb_basis_mat).to_4x4() @ Matrix(
            np.identity(3) * bb_dim / 2).to_4x4()

        bb_mesh = bpy.data.meshes.new(obj.name + "_minimum_bounding_box")
        bb_mesh.from_pydata(vertices=list(self.gen_cube_verts()), edges=[], faces=CUBE_FACE_INDICES)
        bb_mesh.validate()
        bb_mesh.transform(mat)
        bb_mesh.update()
        bb_obj = bpy.data.objects.new(bb_mesh.name, bb_mesh)
        bb_obj.display_type = "WIRE"
        bb_obj.matrix_world = obj.matrix_world

        return bb_obj


    def __init__(self):
        super().__init__()
        self.use_modifier_stack = True
        self.use_global_local_switches = True

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)

        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}

        scene = context.scene

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}
    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        scene = context.scene
        self.type_suffix = self.prefs.boxColSuffix

        #List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []


        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            context.view_layer.objects.active = obj
            bounding_box_data = {}

            new_collider = self.obj_rotating_calipers(obj)

            new_collider.parent = obj
            alignObjects(new_collider, obj)


            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = obj.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = obj.name
            new_name = super().collider_name(basename=parent_name)
            new_collider.name = new_name

            new_collider.data.name = new_name + self.data_suffix
            new_collider.data.name = new_name + self.data_suffix

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        super().print_generation_time("Aligned Box Collider")

        return {'RUNNING_MODAL'}