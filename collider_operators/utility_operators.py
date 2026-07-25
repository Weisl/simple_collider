import bpy
from bpy.props import IntProperty
from mathutils import Matrix

from ..properties.constants import DECIMATE_NAME


def set_triangle_count_limit(obj, target_triangles, iterations=8, depsgraph=None):
    """Adjust obj's Decimate modifier ratio so the evaluated triangle count is
    at or below target_triangles.

    Returns True if the target was reached, False if it isn't reachable even
    at maximum decimation (in which case the ratio is left at 1.0).
    """
    if obj.type != 'MESH':
        return True

    if depsgraph is None:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    if obj.modifiers.get(DECIMATE_NAME):
        decimate = obj.modifiers.get(DECIMATE_NAME)
    else:
        decimate = obj.modifiers.new(name=DECIMATE_NAME, type='DECIMATE')
    decimate.decimate_type = 'COLLAPSE'

    def get_tri_count(ratio):
        decimate.ratio = ratio
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        count = sum(len(p.vertices) - 2 for p in mesh.polygons)
        obj_eval.to_mesh_clear()
        return count

    # If original mesh is already within budget, no decimation needed
    original_count = get_tri_count(1.0)
    if original_count <= target_triangles:
        decimate.ratio = 1.0
        return True

    # Check if even maximum decimation can reach the target
    if get_tri_count(0.001) > target_triangles:
        decimate.ratio = 1.0
        return False

    # Linear estimate: COLLAPSE decimation reduces tris roughly proportional to ratio.
    estimated_ratio = target_triangles / original_count
    actual_count = get_tri_count(estimated_ratio)

    # Narrow binary search correction around the estimate.
    # The search range is a small band rather than the full 0–1 space,
    # so `iterations` steps give much finer precision than searching 0-1 directly.
    if actual_count <= target_triangles:
        lo, hi = estimated_ratio, 1.0
        best_ratio = estimated_ratio
    else:
        lo, hi = 0.001, estimated_ratio
        best_ratio = 0.001

    for _ in range(iterations):
        mid = (lo + hi) * 0.5
        if get_tri_count(mid) <= target_triangles:
            best_ratio = mid
            lo = mid
        else:
            hi = mid

    decimate.ratio = best_ratio
    return True


def move_origin_to_parent(obj):
    """Move obj's origin to match its parent's, baking the offset into the
    mesh data so the object's world-space appearance is unchanged."""
    if obj.type != 'MESH' or obj.parent is None:
        return

    parent = obj.parent
    parent_world = parent.matrix_world.copy()
    child_world = obj.matrix_world.copy()
    offset = child_world.inverted() @ parent_world
    obj.data.transform(offset.inverted())
    obj.data.update()
    obj.matrix_world = parent_world


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
        # Cache depsgraph once for all objects to avoid O(N^2) re-evaluations
        depsgraph = context.evaluated_depsgraph_get()

        unreachable = []
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if not set_triangle_count_limit(obj, self.target_triangles, self.iterations, depsgraph):
                unreachable.append(obj.name)

        if unreachable:
            self.report({'WARNING'},
                        f"Cannot reach {self.target_triangles} tris even at maximum decimation: "
                        f"{', '.join(unreachable)}")

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
        for obj in context.selected_objects:
            move_origin_to_parent(obj)

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


def fix_inverse_matrix_is_safe(obj, tol=1e-4):
    """Whether fix_inverse_matrix() can bake obj's parent-relative transform
    without losing information.

    obj.matrix_world already equals parent.matrix_world @ matrix_parent_inverse
    @ matrix_basis, so the parent's *current* world matrix always cancels out
    algebraically when fix_inverse_matrix() computes
    parent.matrix_world.inverted() @ obj.matrix_world -- the parent's live scale
    is not actually what determines safety. What matters is whether that
    composite matrix (effectively matrix_parent_inverse @ matrix_basis, frozen
    from whenever the parent relationship was last set) contains shear: a
    non-uniform scale combined with a rotation, anywhere in the ancestor chain,
    at the moment matrix_parent_inverse was captured. Blender's loc/rot/scale
    decomposition cannot represent shear, so this is verified directly with a
    decompose-and-reconstruct round trip rather than inspecting parent.scale.
    """
    parent = obj.parent
    if parent is None:
        return True
    composite = parent.matrix_world.inverted() @ obj.matrix_world
    loc, rot, scale = composite.decompose()
    reconstructed = Matrix.LocRotScale(loc, rot, scale)

    composite_3x3 = composite.to_3x3()
    reconstructed_3x3 = reconstructed.to_3x3()
    magnitude = max(abs(composite_3x3[r][c]) for r in range(3) for c in range(3))
    if magnitude < 1e-8:
        return True
    max_diff = max(abs(reconstructed_3x3[r][c] - composite_3x3[r][c]) for r in range(3) for c in range(3))
    return (max_diff / magnitude) <= tol


def fix_inverse_matrix(obj, update_depsgraph=True):
    """Clear obj's matrix_parent_inverse (so the parent-child relationship
    survives exporters like FBX/glTF that don't preserve it) while keeping
    obj.matrix_world unchanged.

    This only re-expresses the existing parent-relative transform on
    obj.location/rotation_euler/scale - it must NOT bake anything into the
    mesh or zero the transform. UBX_/USP_/UCP_ colliders (Unreal's box/
    sphere/capsule collision convention, as opposed to arbitrary UCX_ convex
    hulls) rely on their local vertex data staying a canonical, axis-aligned
    primitive, with position and rotation carried entirely by the object's
    transform. Baking the transform into vertex coordinates instead (the
    previous implementation) desynchronizes the two: the primitive's local
    shape stops being axis-aligned while the transform reads as identity, so
    engines that read shape from vertices and placement from the transform
    reconstruct the wrong box/sphere/capsule.
    """
    # Make a copy of the object's original world matrix before we reset any of its transform matrices
    ob_matrix_orig = obj.matrix_world.copy()
    # Reset parent inverse matrix
    obj.matrix_parent_inverse.identity()
    # Calculate the difference between the parent and child world transforms and
    # set the object's basis matrix to the value of this difference
    obj.matrix_basis = obj.parent.matrix_world.inverted() @ ob_matrix_orig

    # Tag the object for update
    obj.update_tag()
    if update_depsgraph:
        bpy.context.view_layer.update()

    return


class COLLISION_OT_ReloadAddon(bpy.types.Operator):
    """Reload all Simple Collider scripts"""
    bl_idname = "collision.reload_addon"
    bl_label = "Reload Addon"
    bl_description = "Reload all Simple Collider scripts"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        import importlib
        import sys

        root_pkg = __package__.rsplit(".", 1)[0]

        mod_names = sorted(
            [name for name in sys.modules
             if name == root_pkg or name.startswith(root_pkg + ".")],
            key=lambda n: (-n.count("."), n),
        )

        def _do_reload():
            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "unregister"):
                try:
                    root_mod.unregister()
                except Exception as exc:
                    print(f"[Simple Collider] unregister error: {exc}")

            # mod_names is only an approximate dependency order (deepest
            # modules first, alphabetical among ties). Modules that import
            # symbols from a sibling module which happens to sort later
            # (e.g. preferences.py doing `from .prefs_properties import X`,
            # where "preferences" < "prefs_properties" alphabetically) would
            # rebind to that sibling's pre-reload state. A second full pass
            # re-executes every module again, by which point every sibling
            # has already been refreshed at least once, so stale bindings
            # from pass 1 get corrected.
            for _pass in range(2):
                for name in mod_names:
                    mod = sys.modules.get(name)
                    if mod is not None:
                        try:
                            importlib.reload(mod)
                        except Exception as exc:
                            print(f"[Simple Collider] reload error for '{name}': {exc}")

            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "register"):
                try:
                    root_mod.register()
                except Exception as exc:
                    print(f"[Simple Collider] register error: {exc}")

            print(f"[Simple Collider] Reloaded {len(mod_names)} modules from '{root_pkg}'")

        bpy.app.timers.register(_do_reload, first_interval=0.0)
        self.report({'INFO'}, f"Queued reload of {len(mod_names)} modules…")
        return {'FINISHED'}


class COLLISION_OT_FixColliderTransform(bpy.types.Operator):
    """Fix the parent inverse matrix on selected colliders"""
    bl_idname = "object.fix_parent_inverse_transform"
    bl_label = "Fix Parent Inverse Matrix"
    bl_description = "Reset the parent inverse matrix, keeping the transform on the object (not baked into mesh data)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        fixed_count = 0
        skipped_names = []
        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.parent:
                continue
            if fix_inverse_matrix_is_safe(obj):
                fix_inverse_matrix(obj)
                fixed_count += 1
            else:
                print(f"Skipping {obj.name}: parent-relative transform contains shear that "
                      f"can't be baked without distorting the mesh.")
                skipped_names.append(obj.name)

        if skipped_names:
            self.report(
                {'WARNING'},
                f"Fixed {fixed_count} collider(s). Skipped {len(skipped_names)} whose parent-relative "
                f"transform contains shear and can't be reset safely: {', '.join(skipped_names)}.",
            )
        else:
            self.report({'INFO'}, f"Fixed parent inverse matrix for {fixed_count} collider(s).")
        return {'FINISHED'}
