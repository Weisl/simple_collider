import bgl
import blf
import bpy
import gpu
from bpy.props import (
    EnumProperty,
    FloatProperty,
    FloatVectorProperty
)

from .object_functions import add_displace_mod
from ..pyshics_materials.material_functions import remove_materials, set_material


def draw_viewport_overlay(self, context):
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 30, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Space: " + self.my_space)

    blf.position(font_id, 30, 60, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Offset: " + str(self.my_offset))

    blf.position(font_id, 30, 90, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Opacity: " + str(self.my_color[3]))

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

    # Display setting of the bounding object in the viewport
    my_collision_shading_view: EnumProperty(
        name="Shading",
        items=(
            ('SOLID', "SOLID", "SOLID"),
            ('WIRE', "WIRE", "WIRE"),
            ('BOUNDS', "BOUNDS", "BOUNDS"),
        )
    )

    # Tranformation space to be used for creating the bounding object.
    my_space: EnumProperty(
        name="Axis",
        items=(
            ('LOCAL', "LOCAL", "LOCAL"),
            ('GLOBAL', "GLOBAL", "GLOBAL")),
        default="GLOBAL"
    )

    # The offset used in a displacement modifier on the bounding object to
    # either push the bounding object inwards or outwards
    my_offset: FloatProperty(
        name="Bounding Surface Offset",
        default=0.0
    )

    # The object color for the bounding object
    my_color: FloatVectorProperty(
        name="Bounding Object Color", description="", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    def set_viewport_drawing(self, context, bounding_object, physics_material_name):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        bounding_object.display_type = self.my_collision_shading_view
        bounding_object.color = self.my_color
        add_displace_mod(bounding_object, self.my_offset)
        remove_materials(bounding_object)
        set_material(bounding_object, physics_material_name)

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

        # save initial selection and active object to recalculate collisions and restore initial state on cancel
        self.active_obj = context.object
        self.selected_objects = context.selected_objects.copy()

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

        self.execute(context)
