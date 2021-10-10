import bpy

from . import add_bounding_primitive
from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_sphere
from . import add_collision_mesh
from . import visibility_control

classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    add_bounding_sphere.OBJECT_OT_add_bounding_sphere,
    visibility_control.COLLISION_OT_Visibility,
    add_bounding_convex_hull.OBJECT_OT_add_convex_hull,
    add_collision_mesh.OBJECT_OT_add_mesh_collision
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

    # Tranformation space to be used for creating the bounding object.
    scene.my_use_modifier_stack = bpy.props.BoolProperty(
        name="Use Modifier",
        default=False,
    )



    scene.my_hide = bpy.props.BoolProperty(
        name="Hide Boungind Object After Creation",
        default=False
    )

    # The object color for the bounding object
    scene.my_color = bpy.props.FloatVectorProperty(
        name="Bounding Object Color", description="", default=(0.36, 0.5, 1, 0.25), min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    # The object color for the bounding object
    scene.my_color_simple = bpy.props.FloatVectorProperty(
        name="Bounding Object Color", description="", default=(0.5, 1, 0.36, 0.25), min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    # The object color for the bounding object
    scene.my_color_complex = bpy.props.FloatVectorProperty(
        name="Bounding Object Color", description="", default=(1, 0.36, 0.36, 0.25), min=0.0, max=1.0,
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
    del scene.displace_my_offset
