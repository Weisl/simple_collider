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


class COLLISION_OT_ReplaceWithCleanMesh(bpy.types.Operator):
    bl_idname = "collision.replace_with_clean_mesh"
    bl_label = "Replace with Clean Mesh"
    bl_description = "Replace selected objects with new meshes that have clean transformation and matrices while preserving materials, modifiers, and custom properties."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue

            # Store the original mesh data
            original_mesh = obj.data
            original_world_matrix = obj.matrix_world.copy()

            # Store the original name
            original_name = obj.name

            # Store materials and modifiers
            original_materials = obj.data.materials[:] if obj.data.materials else []
            original_modifiers = obj.modifiers[:] if obj.modifiers else []

            # Calculate the inverse of the original world matrix
            inverse_world_matrix = original_world_matrix.inverted()

            # Create a new mesh with vertices in object space
            new_mesh = bpy.data.meshes.new("CleanMesh")
            vertices = [inverse_world_matrix @ original_world_matrix @ v.co for v in original_mesh.vertices]
            polygons = [p.vertices for p in original_mesh.polygons]
            new_mesh.from_pydata(vertices, [], polygons)
            new_mesh.update()

            # Create a new object with a temporary name
            temp_name = "TempObject"
            new_obj = bpy.data.objects.new(temp_name, new_mesh)

            # Link the new object to the scene
            context.collection.objects.link(new_obj)

            # Ensure the new object has clean transformation matrices
            new_obj.matrix_parent_inverse.identity()
            new_obj.matrix_basis.identity()
            new_obj.matrix_local.identity()

            # Position the new object at the original object's location
            new_obj.matrix_world = original_world_matrix

            # Copy materials from the original object to the new one
            if original_materials:
                new_obj.data.materials.clear()
                for material in original_materials:
                    new_obj.data.materials.append(material)

            # Copy modifiers from the original object to the new one
            if original_modifiers:
                for modifier in original_modifiers:
                    new_modifier = new_obj.modifiers.new(modifier.name, modifier.type)
                    # Copy modifier settings
                    for prop in modifier.bl_rna.properties:
                        if not prop.is_readonly:
                            setattr(new_modifier, prop.identifier, getattr(modifier, prop.identifier))

            # Explicitly copy only the custom properties we care about
            custom_props_to_copy = ["collider_group", "collider_shape", "isCollider"]
            for prop in custom_props_to_copy:
                if prop in obj:
                    new_obj[prop] = obj[prop]

            # Set the display type to wireframe for better visibility
            display_props = ["display_type", "color", "show_wire", "show_all_edges"]
            for prop in display_props:
                if prop in obj:
                    new_obj[prop] = obj[prop]

            # Add the new object to the selection
            new_obj.select_set(True)

            # Remove the original object from the scene
            bpy.data.objects.remove(obj)

            # Rename the new object to the original object's name
            new_obj.name = original_name

        self.report({'INFO'}, "Objects replaced with clean mesh")
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
