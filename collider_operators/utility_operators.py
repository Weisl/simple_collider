import bpy
from bpy.props import IntProperty

from ..properties.constants import DECIMATE_NAME


class COLLISION_OT_adjust_decimation(bpy.types.Operator):
    """Adjust Decimation to Target Triangle Count"""
    bl_idname = "object.adjust_decimation"
    bl_label = "Limit Tris Count"
    bl_options = {'REGISTER', 'UNDO'}

    target_triangles: IntProperty(
        name="Target Triangles",
        description="Target number of triangles",
        default=256,
        min=1
    )

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # Add a decimate modifier
                if obj.modifiers.get(DECIMATE_NAME):
                    decimate = obj.modifiers.get(DECIMATE_NAME)
                else:
                    decimate = obj.modifiers.new(name=DECIMATE_NAME, type='DECIMATE')
                decimate.decimate_type = 'COLLAPSE'

                # Start with a ratio that is likely too high
                ratio = 1.0

                # Loop to adjust the ratio
                while ratio > 0.001:
                    decimate.ratio = ratio

                    # Use the dependency graph to get the evaluated mesh
                    depsgraph = context.evaluated_depsgraph_get()
                    obj_eval = obj.evaluated_get(depsgraph)
                    mesh_from_eval = obj_eval.to_mesh()

                    # Calculate the current number of triangles
                    current_triangles = sum(len(poly.vertices) - 2 for poly in mesh_from_eval.polygons)
                    print(f"Current triangles: {current_triangles}, Ratio: {ratio}")

                    # Free the evaluated mesh to prevent memory leaks
                    obj_eval.to_mesh_clear()

                    # Check if the current triangle count is below the target
                    if current_triangles < self.target_triangles:
                        print("Target triangle count achieved.")
                        break

                    # If not, halve the ratio
                    ratio /= 2

                if current_triangles >= self.target_triangles:
                    print("Could not reduce triangles below target with ratio > 0.01.")

        return {'FINISHED'}


class COLLISION_OT_MoveOriginToParentOperator(bpy.types.Operator):
    """Apply Parent Transform to Child"""
    bl_idname = "object.origin_to_parent"
    bl_label = "Move Origin to Parent"
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

            # Copy custom properties from the original object to the new one
            if obj.get('custom_properties') is not None:
                new_obj['custom_properties'] = obj['custom_properties']

            # Add the new object to the selection
            new_obj.select_set(True)

            # Remove the original object from the scene
            bpy.data.objects.remove(obj)

            # Rename the new object to the original object's name
            new_obj.name = original_name

        self.report({'INFO'}, "Objects replaced with clean mesh")
        return {'FINISHED'}


class COLLISION_OT_FixColliderTransform(bpy.types.Operator):
    bl_idname = "object.fix_collider_transform"
    bl_label = "Fix Collider Transform"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type != 'MESH' or not obj.parent:
                continue

            mesh = obj.data
            # Make a copy of the object's original world matrix before we reset any of its transform matrices
            ob_matrix_orig = obj.matrix_world.copy()
            # Reset parent inverse matrix
            obj.matrix_parent_inverse.identity()
            # Calculate the difference between the parent and child world transforms and
            # set the object's basis matrix to the value of this difference
            obj.matrix_basis = obj.parent.matrix_world.inverted() @ ob_matrix_orig
            # Apply the object's basis matrix to the mesh vertices
            transformed_vertices = [obj.matrix_basis @ v.co for v in mesh.vertices]
            mesh.vertices.foreach_set("co", [coord for v in transformed_vertices for coord in v])

            # Reset the object's basis matrix and local matrix
            obj.matrix_basis.identity()
            obj.matrix_local.identity()

            mesh.update()

        self.report({'INFO'}, "Fixed collider transform for selected objects")
        return {'FINISHED'}
