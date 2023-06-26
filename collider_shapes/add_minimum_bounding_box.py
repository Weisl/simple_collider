import bmesh
import bpy
import math
import numpy as np
from bpy.types import Operator
from mathutils import Matrix, Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

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
    bl_idname = "mesh.add_minimum_bounding_box"
    bl_label = "Oriented Minimum BBox"
    bl_description = 'Create oriented minimum bounding box colliders based on the selection'

    @staticmethod
    def gen_cube_verts():
        for x in range(-1, 2, 2):
            for y in range(-1, 2, 2):
                for z in range(-1, 2, 2):
                    yield x, y, z

    @staticmethod
    def rotating_calipers(hull_points: np.ndarray, bases):
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

    @classmethod
    def obj_rotating_calipers(cls, obj):

        bm = bmesh.new()
        dg = bpy.context.evaluated_depsgraph_get()
        bm.from_object(obj, dg)

        chull_out = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        chull_geom = chull_out["geom"]
        chull_points = np.array([bmelem.co for bmelem in chull_geom if isinstance(bmelem, bmesh.types.BMVert)])

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

        bb_basis, bb_max, bb_min = cls.rotating_calipers(chull_points, bases)
        bm.free()
        bb_basis_mat = bb_basis.T

        if bb_min is None or bb_max is None:
            return None, None

        bb_dim = bb_max - bb_min
        bb_center = (bb_max + bb_min) / 2
        rotation_matrix = Matrix(bb_basis_mat).to_4x4()

        mesh_matrix = Matrix.Translation(bb_center.dot(bb_basis)) @ rotation_matrix @ Matrix(
            np.identity(3) * bb_dim / 2).to_4x4()

        bb_mesh = bpy.data.meshes.new(obj.name + "_minimum_bounding_box")
        bb_mesh.from_pydata(vertices=list(cls.gen_cube_verts()), edges=[], faces=CUBE_FACE_INDICES)
        bb_mesh.validate()
        bb_mesh.transform(mesh_matrix)
        bb_mesh.update()

        bb_obj = bpy.data.objects.new(bb_mesh.name, bb_mesh)
        bb_obj.matrix_world = obj.matrix_world

        return bb_obj, rotation_matrix

    def __init__(self):
        super().__init__()
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.shape = "box_shape"
        self.use_recenter_origin = True
        self.use_custom_rotation = True

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

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            bounding_box_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices == None:  # Skip object if there is no Mesh data to create the collider
                continue

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # Don't add object if it consists of less than 3 vertices
                if len(used_vertices) < 3:
                    continue

                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'LOCAL', used_vertices)

                # used_vertices uses local space.
                # store data needed to generate a bounding box in a dictionary
                bounding_box_data['parent'] = obj
                bounding_box_data['verts_loc'] = ws_vtx_co

                collider_data.append(bounding_box_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            ws_vtx_co = verts_co
            verts_co = self.transform_vertex_space(ws_vtx_co, self.active_obj)

            # Don't add object if it consists of less than 3 vertices
            if len(ws_vtx_co) > 2:
                bounding_box_data = {}
                bounding_box_data['parent'] = self.active_obj
                bounding_box_data['verts_loc'] = verts_co
                collider_data = [bounding_box_data]

        for bounding_box_data in collider_data:
            # get data from dictionary
            parent = bounding_box_data['parent']
            verts_loc = bounding_box_data['verts_loc']

            bm = bmesh.new()

            for v in verts_loc:
                bm.verts.new(v)  # add a new vert
            me = bpy.data.meshes.new("mesh")
            bm.to_mesh(me)
            bm.free()

            temp_obj = bpy.data.objects.new('temp_debug_objects', me)
            temp_obj.matrix_world = parent.matrix_world

            if self.prefs.debug:
                root_collection = context.scene.collection
                root_collection.objects.link(temp_obj)

            self.apply_transform(temp_obj, rotation=True, scale=True)

            new_collider, rotation_matrix = self.obj_rotating_calipers(temp_obj)

            root_collection = context.scene.collection
            root_collection.objects.link(new_collider)

            self.custom_set_parent(context, parent, new_collider)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            self.col_rotation_matrix_list.append(rotation_matrix)

            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Aligned Box Collider", elapsed_time)
        self.report({'INFO'}, f"Aligned Box Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
