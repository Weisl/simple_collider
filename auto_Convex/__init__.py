import bpy

from . import add_bounding_auto_convex

classes = (
    add_bounding_auto_convex.VHACD_OT_convex_decomposition,
)


def register():
    scene = bpy.types.Scene
    scene.convex_decomp_depth = bpy.props.IntProperty(
        name='Depth',
        description='The amount of convex hull colliders is the square of this number at the max',
        default=3,
        min=1,
        max=32
    )

    scene.maxNumVerticesPerCH = bpy.props.IntProperty(
        name='Verts per Piece',
        description='Maximum number of vertices per convex-hull collider',
        default=16,
        min=4,
        max=64
    )

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
