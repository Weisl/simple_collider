import bpy

from . import add_bounding_auto_convex

classes = (
    add_bounding_auto_convex.VHACD_OT_convex_decomposition,
)


def register():
    scene = bpy.types.Scene

    # -h
    scene.maxHullAmount = bpy.props.IntProperty(name='Amount', description='Maximum number of output convex hulls.',
                                                default=3, min=1, max=32)

    # -v
    scene.maxHullVertCount = bpy.props.IntProperty(name='Verts per Piece',
                                                   description='Maximum number of vertices in the output convex hull. Default value is 64',
                                                   default=16,
                                                   min=4,
                                                   max=64)
    # -r
    scene.voxelresolution = bpy.props.IntProperty(name="Voxel Resolution",
                                                  description=' Total number of voxels to use. Default is 100000',
                                                  default=100000, min=10000, max=64000000)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
