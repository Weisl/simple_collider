bl_info = {
    "name": "CollisionTool",
    "description": "",
    "author": "Matthias Patscheider",
    "version": (0, 5, 0),
    "blender": (2, 81, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


import bpy, bmesh
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

colSuffix = "COL_"

def getBoundingBox(obj):
    return obj.bound_box

def add_object(context, vertices, newName):
    verts = vertices
    edges = []
    faces = [[0, 1, 2, 3],[7,6,5,4],[5,6,2,1],[0,3,7,4],[3,2,6,7],[4,5,1,0]]

    mesh = bpy.data.meshes.new(name=newName)
    mesh.from_pydata(verts, edges, faces)
    # useful for development when the mesh may be invalid.
    # mesh.validate(verbose=True)
    newObj = object_data_add(context, mesh, operator=None, name=None) # links to object instance

    return newObj

def alignObjects(new, old):
    new.matrix_world = old.matrix_world



def boxColliderPerObject(context):
    global colSuffix

    active_ob = bpy.context.active_object
    selectedObjects = bpy.context.selected_objects.copy()
    colliderOb = []

    for i, obj in enumerate(selectedObjects):
        bBox = getBoundingBox(obj)  # create BoundingBox object for collider
        newCollider = add_object(context, bBox, obj.name + colSuffix)

        # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
        # global_bbox_center = obj.matrix_world @ local_bbox_center
        centre =  sum((Vector(b) for b in obj.bound_box), Vector())
        print ('CENTRE' + str(centre))
        centre /= 8
        print ('CENTRE 2 ' + str(centre))
        # newCollider.matrix_world = obj.matrix_world * (1 / 8 *

        alignObjects(newCollider, obj)

def cylinderCollider(context):
    global colSuffix

    activeObject = bpy.context.object
    selectedObjects = bpy.context.selected_objects.copy()
    colliderOb = []

    for i, obj in enumerate(selectedObjects):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,
                                            radius=max(context.object.dimensions[0] / 2.0,
                                                       context.object.dimensions[1] / 2.0),
                                            depth=context.object.dimensions[2])
        newCollider = bpy.context.object

        centre =  sum((Vector(b) for b in obj.bound_box), Vector())
        print ('CENTRE' + str(centre))
        centre /= 8
        print ('CENTRE 2 ' + str(centre))
        # newCollider.matrix_world = obj.matrix_world * (1 / 8 *

        alignObjects(newCollider, obj)





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


def add_diamond(context):
    obj = context.edit_object
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


def add_box(context):
    obj = context.edit_object
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


def add_box_from_vertex_face_data(self, context, verts_loc, faces):

    active_ob = bpy.context.object

    #        verts_loc, faces = add_box()
    root_col = bpy.context.scene.collection

    mesh = bpy.data.meshes.new("Box")
    bm = bmesh.new()

    for v_co in verts_loc:
        bm.verts.new(v_co)

    bm.verts.ensure_lookup_table()
    for f_idx in faces:
        bm.faces.new([bm.verts[i] for i in f_idx])

    bm.to_mesh(mesh)
    mesh.update()

    # # add the mesh as an object into the scene with this utility module
    # from bpy_extras import object_utils
    # object_utils.object_data_add(context, mesh, operator=self)
    obj = bpy.data.objects.new("Obj", mesh)
    root_col.objects.link(obj)
    alignObjects(obj,active_ob)

from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)



class OBJECT_OT_add_diamond_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_diamond_collision"
    bl_label = "Add Diamond Collision"
    bl_options = {'REGISTER', 'UNDO'}

    # scale: FloatVectorProperty(
    #     name="scale",
    #     default=(1.0, 1.0, 1.0),
    #     subtype='TRANSLATION',
    #     description="scaling",
    # )

    def execute(self, context):
        verts_loc, faces = add_diamond(context)
        add_box_from_vertex_face_data(self, context,verts_loc, faces)

        return {'FINISHED'}

class OBJECT_OT_add_box_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_box_collision"
    bl_label = "Add Box Collision"
    bl_options = {'REGISTER', 'UNDO'}

    # scale: FloatVectorProperty(
    #     name="scale",
    #     default=(1.0, 1.0, 1.0),
    #     subtype='TRANSLATION',
    #     description="scaling",
    # )

    def execute(self, context):
        verts_loc, faces = add_box(context)
        add_box_from_vertex_face_data(self,context, verts_loc, faces)
        return {'FINISHED'}

class OBJECT_OT_add_box_per_object_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_box_per_object_collision"
    bl_label = "Add Box Collision Ob"
    bl_options = {'REGISTER', 'UNDO'}

    # scale: FloatVectorProperty(
    #     name="scale",
    #     default=(1.0, 1.0, 1.0),
    #     subtype='TRANSLATION',
    #     description="scaling",
    # )

    def execute(self, context):
        boxColliderPerObject(context)
        return {'FINISHED'}

class OBJECT_OT_add_cylinder_per_object_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_cylinder_per_object_collision"
    bl_label = "Add Cylinder Collision Ob"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        cylinderCollider(context)
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
        row.operator("mesh.add_box_collision")
        row = layout.row()
        row.operator("mesh.add_diamond_collision")
        row = layout.row()
        row.operator("mesh.add_cylinder_per_object_collision")
        row = layout.row()
        row.operator("mesh.add_box_per_object_collision")




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
    OBJECT_OT_add_box_collision,
    OBJECT_OT_add_diamond_collision,
    OBJECT_OT_add_cylinder_per_object_collision,
    OBJECT_OT_add_box_per_object_collision,
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
