import bmesh
import bpy
from bpy.types import Operator
from bpy_extras.object_utils import object_data_add
from mathutils import Vector

from CollisionHelpers.operators.object_functions import alignObjects
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

    # useful for development when the mesh may be invalid.
    # mesh.validate(verbose=True)
    newObj = object_data_add(context, mesh, operator=None, name=None)  # links to object instance

    return newObj



def verts_faces_to_bbox_collider(self, context, verts_loc, faces):
    """Create box collider for selected mesh area in edit mode"""

    global tmp_name

    active_ob = context.object
    root_collection = context.scene.collection

    # add new mesh
    mesh = bpy.data.meshes.new(tmp_name)
    bm = bmesh.new()

    #create mesh vertices
    for v_co in verts_loc:
        bm.verts.new(v_co)

    #connect vertices to faces
    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    # update bmesh to draw properly in viewport
    bm.to_mesh(mesh)
    mesh.update()

    # create new object from mesh and link it to collection
    # print("active_ob.name = " + active_ob.name)
    new_collider = bpy.data.objects.new(tmp_name, mesh)
    root_collection.objects.link(new_collider)

    scene = context.scene

    if scene.my_space == 'LOCAL':
        new_collider.parent = active_ob
        alignObjects(new_collider, active_ob)

    #TODO: Remove the object mode switch that is called for every object to make this operation faster.
    else:
        bpy.ops.object.mode_set(mode='OBJECT')
        matrix= new_collider.matrix_world
        new_collider.parent = active_ob
        new_collider.matrix_world = matrix

        bpy.ops.object.mode_set(mode='EDIT')

    return new_collider

class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box Collision"

    def __init__(self):
        super().__init__()
        self.use_space = True
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

        scene = context.scene

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            scene.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            scene.my_space = 'LOCAL'
            self.execute(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        global face_order

        scene = context.scene

        # CLEANUP and INIT
        super().execute(context)

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            # if len(obj.data.vertices) == 0:
            #     continue

            context.view_layer.objects.active = obj
            initial_mod_state = {}

            if obj.mode == "EDIT":
                me = obj.data

                if self.my_use_modifier_stack == False:
                    # Get a BMesh representation
                    bm = bmesh.from_edit_mesh(me)

                else:  # self.my_use_modifier_stack == True

                    # Get mesh information with the modifiers applied
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    bm = bmesh.new()
                    bm.from_object(obj, depsgraph)
                    bm.verts.ensure_lookup_table()

                used_vertices = self.get_vertices(bm, me, preselect_all=False)

                if used_vertices == None: # Skip object if there is no Mesh data to create the collider
                    continue

                positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
                verts_loc = self.generate_bounding_box(positionsX, positionsY, positionsZ)
                new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, face_order)

            else:  # mode == "OBJECT":
                if self.my_use_modifier_stack == False:
                    for mod in obj.modifiers:
                        initial_mod_state[mod.name] = mod.show_viewport
                        mod.show_viewport = False
                    context.view_layer.update()

                if scene.my_space == 'LOCAL':
                    # create BoundingBox object for collider
                    bBox = obj.bound_box
                    new_collider = add_box_object(context, bBox)
                    new_collider.parent = obj
                    alignObjects(new_collider, obj)


                else: # Space == 'Global'
                    context.view_layer.objects.active = obj

                    bpy.ops.object.mode_set(mode='EDIT')
                    me = obj.data

                    if self.my_use_modifier_stack == False:
                        # Get a BMesh representation
                        bm = bmesh.from_edit_mesh(me)

                    else: #self.my_use_modifier_stack == True

                        #Get mesh information with the modifiers applied
                        depsgraph = bpy.context.evaluated_depsgraph_get()
                        bm = bmesh.new()
                        bm.from_object(obj, depsgraph)
                        bm.verts.ensure_lookup_table()

                    used_vertices = self.get_vertices(bm, me, preselect_all=True)

                    if used_vertices == None: # Skip object if there is no Mesh data to create the collider
                        continue

                    positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
                    verts_loc = self.generate_bounding_box(positionsX, positionsY, positionsZ)
                    new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, face_order)

                # Reset modifiers of target mesh to initial state
                if self.my_use_modifier_stack == False:
                    for mod_name, value in initial_mod_state.items():
                        obj.modifiers[mod_name].show_viewport = value

            # Name generation
            type_suffix = self.prefs.boxColSuffix
            new_collider.name = super().collider_name(context, type_suffix)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            self.primitive_postprocessing(context, new_collider, self.physics_material_name)
            collections = obj.users_collection
            self.add_to_collections(new_collider, collections)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)

        return {'RUNNING_MODAL'}
