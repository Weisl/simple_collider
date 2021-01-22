import bpy

from . import add_bounding_box
from . import add_bounding_cylinder
from . import add_bounding_primitive
from . import visibility_control

classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    visibility_control.COLLISION_OT_Visibility,
)


def register():
    scene = bpy.types.Scene

    # Display setting of the bounding object in the viewport
    scene.my_collision_shading_view = bpy.props.EnumProperty(
        name="Shading",
        items=(
            ('SOLID', "SOLID", "SOLID"),
            ('WIRE', "WIRE", "WIRE"),
            ('BOUNDS', "BOUNDS", "BOUNDS")),
        default="SOLID"
    )

    # Tranformation space to be used for creating the bounding object.
    scene.my_space = bpy.props.EnumProperty(
        name="Axis",
        items=(
            ('LOCAL', "LOCAL", "LOCAL"),
            ('GLOBAL', "GLOBAL", "GLOBAL")),
        default="GLOBAL"
    )

    scene.my_hide = bpy.props.BoolProperty(
        name="Hide Boungind Object After Creation",
        default = False
    )

    # The offset used in a displacement modifier on the bounding object to
    # either push the bounding object inwards or outwards
    scene.my_offset = bpy.props.FloatProperty(
        name="Bounding Surface Offset",
        default=0.0
    )

    # The object color for the bounding object
    scene.my_color = bpy.props.FloatVectorProperty(
        name="Bounding Object Color", description="", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    del scene.my_collision_shading_view
    del scene.my_color
    del scene.my_space
    del scene.my_offset
