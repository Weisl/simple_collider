import bgl
import blf
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
    blf.draw(font_id, "Shrink/Inflate (S): " + str(scene.my_offset))

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

    def set_viewport_drawing(self, context, bounding_object):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        scene = context.scene

        bounding_object.display_type = 'SOLID'
        bounding_object.color = scene.my_color

    def add_bounding_modifiers(self, context, bounding_object):
        scene = context.scene

        # add displacement modifier and safe it to manipulate the strenght in the modal operator
        mod = add_displace_mod(bounding_object, scene.my_offset)
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

        # store mouse position
        self.first_mouse_x = event.mouse_x

        self.execute(context)
