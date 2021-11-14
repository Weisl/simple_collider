import bpy

from . import add_bounding_primitive
from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_sphere
from . import add_collision_mesh
from . import visibility_and_selection
from . import conversion_operators

classes = (
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    add_bounding_sphere.OBJECT_OT_add_bounding_sphere,
    visibility_and_selection.COLLISION_OT_Visibility,
    visibility_and_selection.COLLISION_OT_Selection,
    add_bounding_convex_hull.OBJECT_OT_add_convex_hull,
    add_collision_mesh.OBJECT_OT_add_mesh_collision,
    conversion_operators.OBJECT_OT_convert_to_collider,
    conversion_operators.OBJECT_OT_convert_to_mesh,
)

def register():
    scene = bpy.types.Scene
    obj = bpy.types.Object

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

    scene.my_space = bpy.props.EnumProperty(
        name="Axis",
        items=(
            ('LOCAL', "LOCAL", "LOCAL"),
            ('GLOBAL', "GLOBAL", "GLOBAL")),
        default="GLOBAL"
    )

    obj.basename = bpy.props.StringProperty(default='', name='')

    obj.collider_type = bpy.props.EnumProperty(name="Shading",default='BOX', items=[
        ('BOX', "Box", "Box"),
        ('SHERE', "Sphere", "Sphere"),
        ('MESH', "Mesh", "Mesh"),
        ('CONVEX', "CONVEX", "CONVEX")])

    obj.collider_complexity = bpy.props.EnumProperty(
        name="collider complexity",
        items=[
            ('SIMPLE_COMPLEX', "SIMPLE_COMPLEX", "SIMPLE_COMPLEX"),
            ('SIMPLE', "SIMPLE", "SIMPLE"),
            ('COMPLEX', "COMPLEX", "COMPLEX")],
        default="SIMPLE_COMPLEX")



    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    obj = bpy.types.Object

    del scene.my_collision_shading_view
    del scene.my_space
    del scene.my_hide
    del scene.my_color
    del scene.my_color_simple
    del scene.my_color_complex
    del scene.my_space

    del obj.basename
    del obj.collider_type
    del obj.collider_complexity
