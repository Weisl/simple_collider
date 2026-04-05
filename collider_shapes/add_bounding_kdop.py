import bmesh
import bpy
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'kdop_collider'

def get_10dop_normals():
    # 5 slab directions = 10 half-space planes
    return [
        Vector((1, 0, 0)),  Vector((-1, 0, 0)),
        Vector((0, 1, 0)),  Vector((0, -1, 0)),
        Vector((0, 0, 1)),  Vector((0, 0, -1)),
        Vector((1, 1, 0)).normalized(),  Vector((-1, -1, 0)).normalized(),  # was missing
        Vector((0, 1, 1)).normalized(),  Vector((0, -1, -1)).normalized(),  # was missing
    ]

def get_18dop_normals():
    normals = []
    normals.extend([
        Vector((1, 0, 0)), Vector((-1, 0, 0)),
        Vector((0, 1, 0)), Vector((0, -1, 0)),
        Vector((0, 0, 1)), Vector((0, 0, -1)),
    ])
    normals.extend([
        Vector((1, 1, 0)).normalized(),
        Vector((1, -1, 0)).normalized(),
        Vector((-1, 1, 0)).normalized(),
        Vector((-1, -1, 0)).normalized(),
        Vector((1, 0, 1)).normalized(),
        Vector((1, 0, -1)).normalized(),
        Vector((-1, 0, 1)).normalized(),
        Vector((-1, 0, -1)).normalized(),
        Vector((0, 1, 1)).normalized(),
        Vector((0, 1, -1)).normalized(),
        Vector((0, -1, 1)).normalized(),
        Vector((0, -1, -1)).normalized(),
    ])
    return normals

def get_26dop_normals():
    normals = get_18dop_normals()
    normals.extend([
        Vector((1, 1, 1)).normalized(),
        Vector((1, 1, -1)).normalized(),
        Vector((1, -1, 1)).normalized(),
        Vector((1, -1, -1)).normalized(),
        Vector((-1, 1, 1)).normalized(),
        Vector((-1, 1, -1)).normalized(),
        Vector((-1, -1, 1)).normalized(),
        Vector((-1, -1, -1)).normalized(),
    ])
    return normals

def generate_kdop(bm_input, normals):
    """Generate k-DOP by intersecting half-spaces via plane clipping."""
    verts = [v.co.copy() for v in bm_input.verts]
    if not verts:
        return bmesh.new()

    # Each normal n defines a half-space: n·x <= d_max
    planes = [(n, max(v.dot(n) for v in verts)) for n in normals]

    # Seed geometry: a cube large enough to contain the final k-DOP
    max_extent = max(abs(c) for v in verts for c in v)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=(max_extent + 1.0) * 6)

    for n, d in planes:
        # Geometry refs must be refreshed each iteration — stale refs cause silent failures
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(
            bm,
            geom=geom,
            dist=1e-5,
            plane_co=n * d,
            plane_no=n,
            clear_outer=True,
            clear_inner=False,
        )
        # Fill the open loop left by this cut BEFORE the next bisect runs.
        # Without this, subsequent cuts operate on a mesh with holes and
        # progressively destroy it until nothing remains.
        bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)

    return bm

class OBJECT_OT_add_bounding_kdop(OBJECT_OT_add_bounding_object, Operator):
    """Create K-Discrete Oriented Polytope (k-DOP) colliders based on the selection"""
    bl_idname = "mesh.add_bounding_kdop"
    bl_label = "Add K-DOP"
    bl_description = 'Create K-DOP colliders based on the selection'

    dop_type: bpy.props.EnumProperty(
        name="k-DOP Type",
        description="Type of k-DOP to generate",
        items=[
            ('10', "10-DOP", "Generate a 10-DOP collider"),
            ('18', "18-DOP", "Generate an 18-DOP collider"),
            ('26', "26-DOP", "Generate a 26-DOP collider"),
        ],
        default='18',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_modifier_stack = True
        self.shape = 'convex_shape'
        self.initial_shape = 'convex_shape'

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

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)
        # change k-DOP type
        elif event.type == 'O' and event.value == 'RELEASE':
            if self.dop_type == '10':
                self.dop_type = '18'
            elif self.dop_type == '18':
                self.dop_type = '26'
            elif self.dop_type == '26':
                self.dop_type = '10'
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        for base_ob, obj in objs:
            convex_collision_data = {}

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                used_vertices = self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh:
                used_vertices = self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                # duplicate object
                convex_collision_data['parent'] = base_ob
                convex_collision_data['verts_loc'] = ws_vtx_co
                collider_data.append(convex_collision_data)
            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                verts_co = verts_co + ws_vtx_co
                convex_collision_data = {}
                convex_collision_data['parent'] = self.active_obj
                convex_collision_data['verts_loc'] = verts_co
                collider_data = [convex_collision_data]

        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for convex_collision_data in collider_data:
            # get data from dictionary
            parent = convex_collision_data['parent']
            verts_loc = convex_collision_data['verts_loc']

            if self.prefs.debug:
                self.create_debug_object_from_verts(context, verts_loc)

            bm = bmesh.new()
            for v in verts_loc:
                bm.verts.new(v)  # add a new vert

            # Select normals based on desired k-DOP type
            if self.dop_type == '10':
                normals = get_10dop_normals()
            elif self.dop_type == '18':
                normals = get_18dop_normals()
            elif self.dop_type == '26':
                normals = get_26dop_normals()

            # Generate k-DOP from the convex hull
            bm_kdop = generate_kdop(bm, normals)

            # Create a new mesh
            me = bpy.data.meshes.new(f"{self.dop_type}-DOP")
            bm_kdop.to_mesh(me)
            bm_kdop.free()
            bm.free()

            new_collider = bpy.data.objects.new('colliders', me)
            context.scene.collection.objects.link(new_collider)

            self.custom_set_parent(context, parent, new_collider)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)
            super().set_collider_name(new_collider, parent.name)

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time(f"{self.dop_type}-DOP Collider", elapsed_time)
        self.report({'INFO'}, f"{self.dop_type}-DOP Collider: {float(elapsed_time):.4f}s")

        return {'RUNNING_MODAL'}
