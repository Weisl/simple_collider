import bpy
from bpy.props import IntProperty

from ..properties.constants import DECIMATE_NAME


class COLLISION_OT_adjust_decimation(bpy.types.Operator):
    """Adjust Decimation to Target Triangle Count"""
    bl_idname = "object.adjust_decimation"
    bl_label = "Limit Tris Count"
    bl_description = "Adjust the decimation modifier to reach a target triangle count"
    bl_options = {'REGISTER', 'UNDO'}

    target_triangles: IntProperty(
        name="Target Triangles",
        description="Target number of triangles",
        default=800,
        min=1
    )

    iterations: IntProperty(
        name="Iterations",
        description="Number of binary search steps. More iterations = closer approximation but slower. Each extra step halves the remaining error",
        default=8,
        min=1,
        max=16,
    )

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            if obj.modifiers.get(DECIMATE_NAME):
                decimate = obj.modifiers.get(DECIMATE_NAME)
            else:
                decimate = obj.modifiers.new(name=DECIMATE_NAME, type='DECIMATE')
            decimate.decimate_type = 'COLLAPSE'

            def get_tri_count(ratio):
                decimate.ratio = ratio
                depsgraph = context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(depsgraph)
                mesh = obj_eval.to_mesh()
                count = sum(len(p.vertices) - 2 for p in mesh.polygons)
                obj_eval.to_mesh_clear()
                return count

            # If original mesh is already within budget, no decimation needed
            original_count = get_tri_count(1.0)
            if original_count <= self.target_triangles:
                decimate.ratio = 1.0
                continue

            # Check if even maximum decimation can reach the target
            if get_tri_count(0.001) > self.target_triangles:
                self.report({'WARNING'}, f"{obj.name}: cannot reach {self.target_triangles} tris even at maximum decimation")
                decimate.ratio = 1.0
                continue

            # Linear estimate: COLLAPSE decimation reduces tris roughly proportional to ratio.
            estimated_ratio = self.target_triangles / original_count
            actual_count = get_tri_count(estimated_ratio)

            # Narrow binary search correction around the estimate.
            # The search range is a small band rather than the full 0–1 space,
            # so self.iterations steps give much finer precision than before.
            if actual_count <= self.target_triangles:
                lo, hi = estimated_ratio, 1.0
                best_ratio = estimated_ratio
            else:
                lo, hi = 0.001, estimated_ratio
                best_ratio = 0.001

            for _ in range(self.iterations):
                mid = (lo + hi) * 0.5
                if get_tri_count(mid) <= self.target_triangles:
                    best_ratio = mid
                    lo = mid
                else:
                    hi = mid

            decimate.ratio = best_ratio

        return {'FINISHED'}


class COLLISION_OT_MoveOriginToParentOperator(bpy.types.Operator):
    """Apply Parent Transform to Child"""
    bl_idname = "object.origin_to_parent"
    bl_label = "Move Origin to Parent"
    bl_description = "Move the collider origin to match its parent object's position"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type != 'MESH' or obj.parent is None:
                continue

            parent = obj.parent
            parent_world = parent.matrix_world.copy()
            child_world = obj.matrix_world.copy()
            offset = child_world.inverted() @ parent_world
            obj.data.transform(offset.inverted())
            obj.data.update()
            obj.matrix_world = parent_world

        self.report({'INFO'}, "Origin moved to parent for selected objects")
        return {'FINISHED'}



def fix_inverse_matrix(obj, update_depsgraph=True):
    from mathutils import Matrix

    mesh = obj.data

    # What the game engine needs as the child's local transform (no MPI involved):
    #   parent_world @ composite @ vertex  ==  child_world @ vertex
    # Using matrix_world is unambiguous — it avoids any uncertainty about whether
    # matrix_local does or does not already incorporate matrix_parent_inverse.
    composite = obj.parent.matrix_world.inverted() @ obj.matrix_world

    # Decompose into a clean TRS (no shear).  decompose() uses polar decomposition
    # and returns the best-fit translation / rotation / scale.  When the parent has
    # scale but no rotation the decomposition is exact (zero residual shear).
    loc, rot, scale = composite.decompose()
    clean_local = Matrix.LocRotScale(loc, rot, scale)

    # The shear residual is whatever the clean TRS cannot represent.
    # Bake it into the mesh vertices so world positions are preserved:
    #   parent_world @ clean_local @ (shear @ v)
    #   = parent_world @ (clean_local @ shear) @ v
    #   = parent_world @ composite @ v  ==  child_world @ v  ✓
    shear = clean_local.inverted() @ composite

    transformed_vertices = [shear @ v.co for v in mesh.vertices]
    mesh.vertices.foreach_set("co", [coord for v in transformed_vertices for coord in v])
    mesh.update()

    # Clear MPI first — Blender computes matrix_basis = MPI.inverted() @ matrix_local
    # when you assign matrix_local.  With MPI already identity the assignment is direct.
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_local = clean_local

    obj.update_tag()
    mesh.update()
    if update_depsgraph:
        bpy.context.view_layer.update()


class COLLISION_OT_FixColliderTransform(bpy.types.Operator):
    """Fix the parent inverse matrix on selected colliders"""
    bl_idname = "object.fix_parent_inverse_transform"
    bl_label = "Fix Parent Inverse Matrix"
    bl_description = "Reset the parent inverse matrix and bake the transform into mesh data"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.parent:
                continue
            fix_inverse_matrix(obj)

        self.report({'INFO'}, "Fixed collider transform for selected objects")
        return {'FINISHED'}
