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
        obj = context.object
        return (
                obj is not None and
                obj.parent is not None and
                obj.type == 'MESH'
        )

    def execute(self, context):
        obj = context.object
        parent = obj.parent

        parent_world = parent.matrix_world.copy()
        child_world = obj.matrix_world.copy()

        offset = child_world.inverted() @ parent_world

        obj.data.transform(offset.inverted())
        obj.data.update()

        obj.matrix_world = parent_world

        return {'FINISHED'}
