import bgl
import blf
import bmesh
import bpy
import gpu

from .object_functions import add_displace_mod
from ..pyshics_materials.material_functions import remove_materials, set_material


def draw_viewport_overlay(self, context):
    scene = context.scene
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    global_orient = "ON" if scene.my_space == 'GLOBAL' else "OFF"
    blf.position(font_id, 30, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Global Orient (G): " + global_orient)

    # draw some text
    local_orient = "ON" if scene.my_space == 'LOCAL' else "OFF"
    blf.position(font_id, 30, 60, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Local Orient (L): " + local_orient)

    blf.position(font_id, 30, 90, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Shrink/Inflate (S): " + str(self.my_offset))

    blf.position(font_id, 30, 120, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Opacity (A) : " + str(scene.my_color[3]))

    blf.position(font_id, 30, 150, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Shading View (S) : " + str(scene.my_collision_shading_view))

    blf.position(font_id, 30, 180, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Hide After Creation (H) : " + str(scene.my_hide))

    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.5))

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)


class OBJECT_OT_add_bounding_object():
    """Abstract parent class to contain common methods and properties for all add bounding object operators"""
    bl_options = {'REGISTER', 'UNDO'}

    # The offset used in a displacement modifier on the bounding object to
    # either push the bounding object inwards or outwards
    my_offset: bpy.props.FloatProperty()

    def remove_objects(self, list):
        # Remove previously created collisions
        if len(list) > 0:
            for ob in list:
                objs = bpy.data.objects
                objs.remove(ob, do_unlink=True)

    def custom_set_parent(self, context, parent, child):
        # set parent
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = parent
        parent.select_set(True)
        child.select_set(True)

        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

    def get_vertices(self, bm, preselect_all=False):
        if preselect_all == True:
            for v in bm.verts: v.select = True

        used_vertives = [v for v in bm.verts if v.select]

        return used_vertives

    def get_point_positions(self, obj, space, used_vertives):
        """ returns vertex and face information for the bounding box based on the given coordinate space (e.g., world or local)"""

        # Modify the BMesh, can do anything here...
        positionsX = []
        positionsY = []
        positionsZ = []

        if space == 'GLOBAL':
            # get world space coordinates of the vertices
            for v in used_vertives:
                v_local = v
                v_global = obj.matrix_world @ v_local.co

                positionsX.append(v_global[0])
                positionsY.append(v_global[1])
                positionsZ.append(v_global[2])

        # space == 'LOCAL'
        else:
            for v in used_vertives:
                positionsX.append(v.co.x)
                positionsY.append(v.co.y)
                positionsZ.append(v.co.z)

        return positionsX, positionsY, positionsZ

    def set_viewport_drawing(self, context, bounding_object):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        scene = context.scene

        bounding_object.display_type = 'SOLID'
        bounding_object.color = scene.my_color

    def add_bounding_modifiers(self, context, bounding_object):
        scene = context.scene

        # add displacement modifier and safe it to manipulate the strenght in the modal operator
        mod = add_displace_mod(bounding_object, self.my_offset)
        self.displace_modifiers.append(mod)

    def set_physics_material(self, context, bounding_object, physics_material_name):
        remove_materials(bounding_object)
        set_material(bounding_object, physics_material_name)

    def cleanup(self, context, bounding_object, physics_material_name):

        self.set_viewport_drawing(context, bounding_object)
        self.add_bounding_modifiers(context, bounding_object)
        self.set_physics_material(context, bounding_object, physics_material_name)

        bounding_object['isCollider'] = True

    def add_to_collections(self, obj, collections):
        old_collection = obj.users_collection

        for col in collections:
            try:
                col.objects.link(obj)
            except RuntimeError:
                pass

        for col in old_collection:
            if col not in collections:
                col.objects.unlink(obj)

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

        # get collision suffix from preferences
        prefs = context.preferences.addons["CollisionHelpers"].preferences
        colSuffix = prefs.colSuffix
        colPreSuffix = prefs.colPreSuffix
        boxColSuffix = prefs.boxColSuffix
        self.name_suffix = colPreSuffix + boxColSuffix + colSuffix

        self.selected_objects = context.selected_objects.copy()

        # save initial selection and active object to recalculate collisions and restore initial state on cancel
        if context.object is not None:
            self.active_obj = context.object
        else:
            context.view_layer.objects.active = self.selected_objects[0]
            self.active_obj = context.object

        # get physics material from properties panel
        scene = context.scene
        self.physics_material_name = scene.CollisionMaterials
        self.previous_objects = []

        # Store shading color type to restore after operator
        self.color_type = context.space_data.shading.color_type
        # Set preview to object color to see transparent collision
        context.space_data.shading.color_type = 'OBJECT'

        # add modal handler
        context.window_manager.modal_handler_add(self)

        # the arguments we pass the the callback
        args = (self, context)
        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_viewport_overlay, args, 'WINDOW', 'POST_PIXEL')

        self.displace_active = False
        self.displace_modifiers = []

        self.opacity_active = False

        # reset displace offset every time calling the operator
        self.my_offset = 0.0

        # store mouse position
        self.first_mouse_x = event.mouse_x

        self.execute(context)

    def modal(self, context, event):
        scene = context.scene

        # User Input
        # aboard operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:

            # Remove previously created collisions
            if self.previous_objects != None:
                for obj in self.previous_objects:
                    objs = bpy.data.objects
                    objs.remove(obj, do_unlink=True)

            context.space_data.shading.color_type = self.color_type

            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            return {'CANCELLED'}

        # apply operator
        elif event.type in {'LEFTMOUSE', 'NUMPAD_ENTER'}:
            # self.execute(context)
            context.space_data.shading.color_type = self.color_type

            for obj in self.previous_objects:
                obj.display_type = scene.my_collision_shading_view
                if scene.my_hide:
                    obj.hide_viewport = scene.my_hide

            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            return {'FINISHED'}

        # hide after creation
        elif event.type == 'H' and event.value == 'RELEASE':
            scene.my_hide = not scene.my_hide
            self.execute(context)

        elif event.type == 'S' and event.value == 'RELEASE':
            self.displace_active = not self.displace_active
            self.opacity_active = False

        elif event.type == 'A' and event.value == 'RELEASE':
            self.opacity_active = not self.opacity_active
            self.displace_active = False

        elif event.type == 'MOUSEMOVE':
            if self.displace_active:
                delta = self.first_mouse_x - event.mouse_x
                for mod in self.displace_modifiers:
                    strenght = 1.0 - delta * 0.01
                    mod.strength = strenght
                    mod.show_on_cage = True
                    mod.show_in_editmode = True

                    # Store displacement strenght to use when regenerating the colliders
                    self.my_offset = mod.strength

            if self.opacity_active:
                delta = self.first_mouse_x - event.mouse_x
                color_alpha = 0.5 + delta * 0.01

                for obj in self.previous_objects:
                    obj.color[3] = color_alpha

                scene.my_color[3] = color_alpha

        # passthrough specific events to blenders default behavior
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}