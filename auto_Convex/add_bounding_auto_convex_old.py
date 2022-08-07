import bpy
import bmesh

from bpy.types import Operator

from os import path as os_path
from subprocess import Popen

from .off_eport import off_export
from ..operators.object_pivot_and_ailgn import alignObjects
from ..operators.add_bounding_primitive import OBJECT_OT_add_bounding_object

class VHACD_OT_convex_decomposition(OBJECT_OT_add_bounding_object, Operator):
    bl_idname = 'collision.vhacd'
    bl_label = 'Convex Decomposition'
    bl_description = 'Split the object collision into multiple convex hulls using Hierarchical Approximate Convex Decomposition'
    bl_options = {'REGISTER', 'PRESET'}

    def set_export_path(self, path):
        self.type_suffix = self.prefs.convexColSuffix

        # Check executable path
        executable_path = bpy.path.abspath(path)
        if os_path.isdir(executable_path):
            executable_path = os_path.join(executable_path, 'testVHACD')
            return executable_path

        elif not os_path.isfile(executable_path):
            self.report({'ERROR'}, 'Path to V-HACD executable required')
            return {'CANCELLED'}

        if not os_path.exists(executable_path):
            self.report({'ERROR'}, 'Cannot find V-HACD executable at specified path')
            return {'CANCELLED'}

        return executable_path

    def set_data_path(self, path):
        # Check data path
        data_path = bpy.path.abspath(path)

        if data_path.endswith('/') or data_path.endswith('\\'):
            data_path = os_path.dirname(data_path)
            return data_path

        if not os_path.exists(data_path):
            self.report({'ERROR'}, 'Invalid data directory')
            return {'CANCELLED'}

        return data_path

    def __init__(self):
        super().__init__()
        self.use_decimation = True
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
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        import addon_utils
        addon_name = 'io_scene_x3d'
        addon_utils.check(addon_name)

        success = addon_utils.enable(addon_name)
        if not success:
            print(addon_name, "is not found")
            return {'CANCELLED'}

        print("enabled", success.bl_info['name'])

        executable_path = self.set_export_path(self.prefs.executable_path)
        data_path = self.set_data_path(self.prefs.data_path)

        scene = bpy.context.scene

        if executable_path == {'CANCELLED'} or data_path == {'CANCELLED'}:
            self.report({'WARNING'}, 'No executable path found!')
            context.space_data.shading.color_type = self.color_type
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            return {'CANCELLED'}

        collider_data = []
        verts_co = []

        for obj in self.selected_objects:
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            convex_collision_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices == None: # Skip object if there is no Mesh data to create the collider
                continue

            if scene.creation_mode == 'INDIVIDUAL':
                convex_collision_data['parent'] = obj

                #only store vertex positions
                verts_loc = [v.co for v in used_vertices]
                convex_collision_data['verts_loc'] = verts_loc

                collider_data.append(convex_collision_data)


            else: #if scene.creation_mode == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if scene.creation_mode == 'SELECTION':

            convex_collision_data = {}
            convex_collision_data['parent'] = self.active_obj
            convex_collision_data['verts_loc'] = verts_co
            collider_data = [convex_collision_data]

        bpy.ops.object.mode_set(mode='OBJECT')

        convex_decomposition_data = []

        for convex_collision_data in collider_data:
            parent = convex_collision_data['parent']
            verts_loc = convex_collision_data['verts_loc']

            bm = bmesh.new()

            for v in verts_loc:
                bm.verts.new(v)  # add a new vert

            mesh = bpy.data.meshes.new("mesh")
            bm.to_mesh(mesh)
            bm.free()

            # Base filename is object name with invalid characters removed
            filename = ''.join(c for c in parent.name if c.isalnum() or c in (' ', '.', '_')).rstrip()

            off_filename = os_path.join(data_path, '{}.off'.format(filename))
            outFileName = os_path.join(data_path, '{}.wrl'.format(filename))
            logFileName = os_path.join(data_path, '{}_log.txt'.format(filename))

            # print('\nExporting mesh for V-HACD: {}...'.format(off_filename))
            off_export(mesh, off_filename)

            cmd_line = ('"{}" --input "{}" --resolution {} --depth {} '
                        '--concavity {:g} --planeDownsampling {} --convexhullDownsampling {} '
                        '--alpha {:g} --beta {:g} --gamma {:g} --pca {:b} --mode {:b} '
                        '--maxNumVerticesPerCH {} --minVolumePerCH {:g} --output "{}" --log "{}"').format(
                executable_path, off_filename, self.prefs.resolution, scene.convex_decomp_depth,
                self.prefs.concavity, self.prefs.planeDownsampling, self.prefs.convexhullDownsampling,
                self.prefs.alpha, self.prefs.beta, self.prefs.gamma, self.prefs.pca, self.prefs.mode == 'TETRAHEDRON',
                scene.maxNumVerticesPerCH, self.prefs.minVolumePerCH, outFileName, logFileName)

            # print('Running V-HACD...\n{}\n'.format(cmd_line))

            vhacd_process = Popen(cmd_line, bufsize=-1, close_fds=True, shell=True)
            bpy.data.meshes.remove(mesh)
            vhacd_process.wait()

            if not os_path.exists(outFileName):
                continue

            # get list of imported assets
            bpy.ops.import_scene.x3d(filepath=outFileName, axis_forward='Y', axis_up='Z')
            imported = bpy.context.selected_objects
            imported = list(set(imported) - set(self.selected_objects))

            for ob in imported:
                ob.select_set(False)

            convex_collisions_data = {}
            convex_collisions_data['colliders'] = imported
            convex_collisions_data['parent'] = parent
            convex_decomposition_data.append(convex_collisions_data)

        context.view_layer.objects.active = self.active_obj

        for convex_collisions_data in convex_decomposition_data:
            convex_collision = convex_collisions_data['colliders']
            parent = convex_collisions_data['parent']
            # post_matrix = convex_collisions_data['post_matrix']

            # print(debug_text)

            for new_collider in convex_collision:
                new_collider.name = super().collider_name(basename=parent.name)

                if scene.creation_mode == 'INDIVIDUAL':
                    self.custom_set_parent(context, parent, new_collider)

                alignObjects(new_collider, parent)

                collections = parent.users_collection
                self.primitive_postprocessing(context, new_collider, collections)
                self.new_colliders_list.append(new_collider)

        if len(self.new_colliders_list) < 1:
            self.report({'WARNING'}, 'No meshes to process!')
            return {'CANCELLED'}

        super().reset_to_initial_state(context)
        print("Time elapsed: ", str(self.get_time_elapsed()))
        return {'FINISHED'}