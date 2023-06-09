import bmesh
import bpy
import math
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'capsule_collider'

# Function to calculate the distance between two points
def distance(p1, p2):
    return math.sqrt(sum((p1[i] - p2[i]) ** 2 for i in range(len(p1))))

# Function to calculate the distance between a point and a line segment
def point_line_segment_distance(p, p1, p2):
    v = [p2[i] - p1[i] for i in range(len(p1))]
    w = [p[i] - p1[i] for i in range(len(p1))]

    t = max(0, min(1, sum(w[i] * v[i] for i in range(len(v))) / sum(v[i] * v[i] for i in range(len(v)))))
    closest_point = [p1[i] + t * v[i] for i in range(len(p1))]
    return distance(p, closest_point)

# Function to calculate the radius and height of the bounding capsule
def calculate_radius_height(points):
    max_distance = 0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            d = distance(points[i], points[j])
            if d > max_distance:
                max_distance = d

    radius = max_distance / 2
    height = max_distance - radius
    return radius, height

class OBJECT_OT_add_bounding_capsule(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding capsule collider based on the selection"""
    bl_idname = "mesh.add_bounding_capsule"
    bl_label = "Add Capsule"
    bl_description = 'Create bounding capsule colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.shape = 'capsule_shape'


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

        return {'RUNNING_MODAL'}

    def execute(self, context):
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            context.view_layer.objects.active = obj
            bounding_capsule_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # used_vertices uses local space.
                co = self.get_point_positions(obj, self.my_space, used_vertices)

                # store data needed to generate a bounding box in a dictionary
                bounding_capsule_data['parent'] = obj
                bounding_capsule_data['verts_loc'] = co

                collider_data.append(bounding_capsule_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_capsule_data in collider_data:
            # get data from dictionary
            parent = bounding_capsule_data['parent']
            verts_loc = bounding_capsule_data['verts_loc']

            # Calculate the radius and height of the bounding capsule
            radius, height = calculate_radius_height(verts_loc)

            # Create a new mesh object for the cylinder
            bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height)
            cylinder = bpy.context.object

            # Create a new mesh object for the top hemisphere
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, height/2))
            top_hemisphere = bpy.context.object

            # Create a new mesh object for the bottom hemisphere
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, -height/2))
            bottom_hemisphere = bpy.context.object

            # Combine the objects into a single object
            bpy.ops.object.select_all(action='DESELECT')
            cylinder.select_set(True)
            top_hemisphere.select_set(True)
            bottom_hemisphere.select_set(True)
            bpy.context.view_layer.objects.active = cylinder
            bpy.ops.object.join()

            # Get the combined object
            new_collider = bpy.context.object

            # Move the bounding capsule to the same location as the original object
            new_collider.location = parent.location

            # Align the bounding capsule with the original object's rotation
            new_collider.rotation_euler = parent.rotation_euler

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = parent.name
            super().set_collider_name(new_collider, parent_name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Capsule Collider", elapsed_time)
        self.report({'INFO'}, f"Capsule Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
