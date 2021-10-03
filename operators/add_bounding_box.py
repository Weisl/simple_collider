import bmesh
import bpy
from bpy.types import Operator
from bpy_extras.object_utils import object_data_add
from mathutils import Vector

from CollisionHelpers.operators.object_functions import alignObjects
from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'tmp_name'

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

    #vertex indizes defining the faces of the cube
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]

    return verts, faces


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
    newCollider = bpy.data.objects.new(tmp_name, mesh)
    root_collection.objects.link(newCollider)

    scene = context.scene

    if scene.my_space == 'LOCAL':
        newCollider.parent = active_ob
        alignObjects(newCollider, active_ob)

    #TODO: Remove the object mode switch that is called for every object to make this operation faster.
    else:
        bpy.ops.object.mode_set(mode='OBJECT')
        self.custom_set_parent(context, active_ob, newCollider)
        bpy.ops.object.mode_set(mode='EDIT')

    return newCollider



class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box Collision"

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True


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
            scene.my_use_modifier_stack = not scene.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = context.scene

        # CLEANUP and INIT
        super().execute(context)




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

            initial_mod_state = {}

            if scene.my_use_modifier_stack == False:
                for mod in obj.modifiers:
                    initial_mod_state[mod.name] = mod.show_viewport
                    mod.show_viewport = False
                context.view_layer.update()

            if obj.mode == "EDIT":
                me = obj.data
                # Get a BMesh representation
                bm = bmesh.from_edit_mesh(me)
                used_vertices = self.get_vertices(bm, preselect_all=False)

                positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
                verts_loc, faces = generate_box(positionsX, positionsY, positionsZ)
                new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, faces)

            else:  # mode == "OBJECT":
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

                    # Get a BMesh representation
                    bm = bmesh.from_edit_mesh(me)
                    used_vertices = self.get_vertices(bm, preselect_all=True)
                    positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, used_vertices)
                    verts_loc, faces = generate_box(positionsX, positionsY, positionsZ)
                    new_collider = verts_faces_to_bbox_collider(self, context, verts_loc, faces)

            # Reset modifiers of target mesh to initial state
            if scene.my_use_modifier_stack == False:
                for mod_name, value in initial_mod_state.items():
                    print("key %s and value %s" % (mod_name, value))
                    obj.modifiers[mod_name].show_viewport = value

            # Name generation
            prefs = context.preferences.addons["CollisionHelpers"].preferences
            type_suffix = prefs.boxColSuffix

            new_collider.name = super().collider_name(context, type_suffix, i)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            self.primitive_postprocessing(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)

        return {'RUNNING_MODAL'}
