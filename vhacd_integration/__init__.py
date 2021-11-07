import bpy
from . import vhacd_operator

classes = (
    vhacd_operator.VHACD_OT_convex_decomposition,
)


def register():

    scene = bpy.types.Scene
    scene.convex_decomp_depth = bpy.props.IntProperty(
        name='Clipping Depth',
        description='Split the object into square of this objects',
        default=2,
        min=1,
        max=32
    )

    scene.maxNumVerticesPerCH = bpy.props.IntProperty(
        name='Maximum Vertices Per CH',
        description='Maximum number of vertices per convex-hull',
        default=32,
        min=4,
        max=1024
    )

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)



def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
