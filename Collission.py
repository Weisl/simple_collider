bl_info = {
    "name": "New Object",
    "author": "Your Name Here",
    "version": (1, 0),
    "blender": (2, 81, 0),
    "location": "View3D > Tools ",
    "warning": "",
    "wiki_url": "https://github.com/Weisl/simple_renaming_panel",
    "tracker_url": "https://github.com/Weisl/simple_renaming_panel/issues",
    "support": "COMMUNITY",
    "category": "Add Mesh",
}


import bpy
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector


def convexHull():
    #	Find the points with minimum and maximum x coordinates, as these will always be part of the convex hull.
    # Use the line formed by the two points to divide the set in two subsets of points, which will be processed recursively.
    # Determine the point, on one side of the line, with the maximum distance from the line. This point forms a triangle with those of the line.
    # The points lying inside of that triangle cannot be part of the convex hull and can therefore be ignored in the next steps.
    # Repeat the previous two steps on the two lines formed by the triangle (not the initial line).
    # Keep on doing so on until no more points are left, the recursion has come to an end and the points selected constitute the convex hull.

    obj = bpy.context.edit_object
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.from_edit_mesh(me)

    selected_verts = [v for v in bm.verts if v.select]
    positionsX = []
    positionsY = []
    positionsZ = []

    i = 0

    VMinX = VMaxX = None

    for v in selected_verts:
        if i == 0:
            VMinX = v
            VMaxX = v
        else:
            if v.co.x < VMinX.co.x:
                VMinX = v
            if v.co.x > VMaxX.co.x:
                VMaxX = v
        i = i + 1

    print(VMinX.co)
    print(VMaxX.co)

    return


def add_diamond():
    obj = bpy.context.edit_object
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.from_edit_mesh(me)

    selected_verts = [v for v in bm.verts if v.select]

    vertSet01 = vertSet02 = vertSet03 = vertSet04 = []

    for v in selected_verts:
        vertSet01.append(v.co.x + v.co.y + v.co.z)
        vertSet02.append(v.co.x - v.co.y + v.co.z)
        vertSet03.append(v.co.x + v.co.y - v.co.z)
        vertSet04.append(v.co.x - v.co.y - v.co.z)

    MMin = min(vertSet01)
    NMin = min(vertSet02)
    OMin = min(vertSet03)
    PMin = min(vertSet04)
    MMax = max(vertSet01)
    NMax = max(vertSet02)
    OMax = max(vertSet03)
    PMax = max(vertSet04)

    verts = [
        (MMin, NMin, OMin),
        (MMin, NMin, OMax),
        (MMax, NMax, OMax),
        (MMax, NMax, OMin),
        (MMin, NMax, OMax),
        (MMin, NMax, OMin),
        (MMax, NMin, OMax),
        (MMax, NMin, OMin),
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]

    return verts, faces


def add_box():
    obj = bpy.context.edit_object
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.from_edit_mesh(me)

    selected_verts = [v for v in bm.verts if v.select]
    vertsLoc = []
    vertsLoc = selected_verts

    #    for v in selected_verts:
    #        v_local = Vector((v))
    #        v_global = obj.matrix_world @ v_local
    #        vertsLoc.append(v_global)
    #
    #    for v in selected_verts:
    #        mat = obj.matrix_world
    #        vertsLoc.append(v.transform(mat))

    # Modify the BMesh, can do anything here...
    positionsX = []
    positionsY = []
    positionsZ = []

    for v in vertsLoc:
        positionsX.append(v.co.x)
        positionsY.append(v.co.y)
        positionsZ.append(v.co.z)

    verts = [
        (max(positionsX), max(positionsY), min(positionsZ)),
        (max(positionsX), min(positionsY), min(positionsZ)),
        (min(positionsX), min(positionsY), min(positionsZ)),
        (min(positionsX), max(positionsY), min(positionsZ)),
        (max(positionsX), max(positionsY), max(positionsZ)),
        (max(positionsX), min(positionsY), max(positionsZ)),
        (min(positionsX), min(positionsY), max(positionsZ)),
        (min(positionsX), max(positionsY), max(positionsZ)),
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]

    return verts, faces


def BBoxEditMode(self, context):
    #        verts_loc, faces = add_box()
    verts_loc, faces = add_diamond()

    mesh = bpy.data.meshes.new("Box")
    bm = bmesh.new()

    for v_co in verts_loc:
        bm.verts.new(v_co)

    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    bm.to_mesh(mesh)
    mesh.update()

    # add the mesh as an object into the scene with this utility module
    from bpy_extras import object_utils
    object_utils.object_data_add(context, mesh, operator=self)


from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)



class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_object"
    bl_label = "Add Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    scale: FloatVectorProperty(
        name="scale",
        default=(1.0, 1.0, 1.0),
        subtype='TRANSLATION',
        description="scaling",
    )

    def execute(self, context):
        convexHull()
        return {'FINISHED'}

class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_object"
    bl_label = "Add Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    scale: FloatVectorProperty(
        name="scale",
        default=(1.0, 1.0, 1.0),
        subtype='TRANSLATION',
        description="scaling",
    )

    def execute(self, context):
        convexHull()
        return {'FINISHED'}

class CollissionPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Hello World Panel"
    bl_idname = "OBJECT_PT_hello"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object

        row = layout.row()
        row.label(text="Hello world!", icon='WORLD_DATA')

        row = layout.row()
        row.label(text="Active object is: " + obj.name)
        row = layout.row()
        row.prop(obj, "name")

        row = layout.row()
        row.operator("mesh.primitive_cube_add")

# Registration

def add_object_button(self, context):
    self.layout.operator(
        OBJECT_OT_add_object.bl_idname,
        text="Add Object",
        icon='PLUGIN')


# This allows you to right click on a button and link to documentation
def add_object_manual_map():
    url_manual_prefix = "https://docs.blender.org/manual/en/latest/"
    url_manual_mapping = (
        ("bpy.ops.mesh.add_object", "scene_layout/object/types.html"),
    )
    return url_manual_prefix, url_manual_mapping

classes = (
    OBJECT_OT_add_object,
    CollissionPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.utils.register_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.utils.unregister_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_button)


if __name__ == "__main__":
    register()
