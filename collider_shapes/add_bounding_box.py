import bmesh
import bpy
from bpy.types import Operator
from bpy_extras.object_utils import object_data_add

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'box_collider'

# vertex indizes defining the faces of the cube
face_order = [
    (0, 1, 2, 3),
    (4, 7, 6, 5),
    (0, 4, 5, 1),
    (1, 5, 6, 2),
    (2, 6, 7, 3),
    (4, 0, 3, 7),
]


def add_box_object(context, vertices):
    """Generate a new object from the given vertices"""

    global tmp_name

    verts = vertices
    edges = []
    faces = [[0, 1, 2, 3], [7, 6, 5, 4], [5, 6, 2, 1], [0, 3, 7, 4], [3, 2, 6, 7], [4, 5, 1, 0]]

    mesh = bpy.data.meshes.new(name=tmp_name)
    mesh.from_pydata(verts, edges, faces)

    return object_data_add(context, mesh, operator=None, name=None)


def verts_faces_to_bbox_collider(self, context, verts_loc, faces):
    """Create box collider for selected mesh area in edit mode"""

    global tmp_name

    # add new mesh
    mesh = bpy.data.meshes.new(tmp_name)
    bm = bmesh.new()

    # create mesh vertices
    for v_co in verts_loc:
        bm.verts.new(v_co)

    # connect vertices to faces
    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    # update bmesh to draw properly in viewport
    bm.to_mesh(mesh)
    mesh.update()

    # create new object from mesh and link it to collection
    new_collider = bpy.data.objects.new(tmp_name, mesh)

    root_collection = context.scene.collection
    root_collection.objects.link(new_collider)

    return new_collider


class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding box collisions based on the selection"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box"
    bl_description = 'Create bounding box colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.shape = 'box_shape'


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

        colSettings = context.scene.collider_tools

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            self.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            self.my_space = 'LOCAL'
            self.execute(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        colSettings = context.scene.collider_tools

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            if obj and obj.type in self.valid_object_types:
                if obj.type is not 'MESH':

                    # store initial state for operation cancel
                    original_obj = obj
                    user_collections = original_obj.users_collection
                    self.original_obj_data.append(self.store_initial_obj_state(original_obj, user_collections))

                    # convert meshes
                    obj = self.convert_to_mesh(context, obj)

            context.view_layer.objects.active = obj
            bounding_box_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # used_vertices uses local space.
                co = self.get_point_positions(obj, self.my_space, used_vertices)
                verts_loc, center_point = self.generate_bounding_box(co)

                # store data needed to generate a bounding box in a dictionary
                bounding_box_data['parent'] = obj
                bounding_box_data['verts_loc'] = verts_loc
                bounding_box_data['center_point'] = center_point

                collider_data.append(bounding_box_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            collider_data = self.selection_bbox_data(verts_co)
        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_box_data in collider_data:
            # get data from dictionary
            parent = bounding_box_data['parent']
            verts_loc = bounding_box_data['verts_loc']
            center_point = bounding_box_data['center_point']

            global face_order
            new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, face_order)
            scene = context.scene

            if self.my_space == 'LOCAL':
                new_collider.parent = parent
                # align collider with parent
                new_collider.matrix_world = parent.matrix_world
                self.use_recenter_origin = False

            else:  # self.my_space == 'GLOBAL':
                self.custom_set_parent(context, parent, new_collider)

                self.use_recenter_origin = True
                self.col_center_loc_list.append(center_point)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = parent.name
            super().set_collider_name(new_collider, parent_name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Box Collider", elapsed_time)
        self.report({'INFO'}, f"Box Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}

    def selection_bbox_data(self, verts_co):
        if self.my_space == 'LOCAL':
            ws_vtx_co = verts_co
            verts_co = self.transform_vertex_space(ws_vtx_co, self.active_obj)

        bbox_verts, center_point = self.generate_bounding_box(verts_co)

        bounding_box_data = {'parent': self.active_obj, 'verts_loc': bbox_verts, 'center_point': center_point}

        return [bounding_box_data]
