# def convexHull():
#     #	Find the points with minimum and maximum x coordinates, as these will always be part of the convex hull.
#     # Use the line formed by the two points to divide the set in two subsets of points, which will be processed recursively.
#     # Determine the point, on one side of the line, with the maximum distance from the line. This point forms a triangle with those of the line.
#     # The points lying inside of that triangle cannot be part of the convex hull and can therefore be ignored in the next steps.
#     # Repeat the previous two steps on the two lines formed by the triangle (not the initial line).
#     # Keep on doing so on until no more points are left, the recursion has come to an end and the points selected constitute the convex hull.
#
#     obj = bpy.context.edit_object
#     me = obj.data
#
#     # Get a BMesh representation
#     bm = bmesh.from_edit_mesh(me)
#
#     selected_verts = [v for v in bm.verts if v.select]
#     positionsX = []
#     positionsY = []
#     positionsZ = []
#
#     i = 0
#
#     VMinX = VMaxX = None
#
#     for v in selected_verts:
#         if i == 0:
#             VMinX = v
#             VMaxX = v
#         else:
#             if v.co.x < VMinX.co.x:
#                 VMinX = v
#             if v.co.x > VMaxX.co.x:
#                 VMaxX = v
#         i = i + 1
#
#     print(VMinX.co)
#     print(VMaxX.co)
#
#     return

#
# def add_diamond(context):
#     obj = context.edit_object
#     me = obj.data
#
#     # Get a BMesh representation
#     bm = bmesh.from_edit_mesh(me)
#
#     selected_verts = [v for v in bm.verts if v.select]
#
#     vertSet01 = vertSet02 = vertSet03 = vertSet04 = []
#
#     for v in selected_verts:
#         vertSet01.append(v.co.x + v.co.y + v.co.z)
#         vertSet02.append(v.co.x - v.co.y + v.co.z)
#         vertSet03.append(v.co.x + v.co.y - v.co.z)
#         vertSet04.append(v.co.x - v.co.y - v.co.z)
#
#     MMin = min(vertSet01)
#     NMin = min(vertSet02)
#     OMin = min(vertSet03)
#     PMin = min(vertSet04)
#     MMax = max(vertSet01)
#     NMax = max(vertSet02)
#     OMax = max(vertSet03)
#     PMax = max(vertSet04)
#
#     verts = [
#         (MMin, NMin, OMin),
#         (MMin, NMin, OMax),
#         (MMax, NMax, OMax),
#         (MMax, NMax, OMin),
#         (MMin, NMax, OMax),
#         (MMin, NMax, OMin),
#         (MMax, NMin, OMax),
#         (MMax, NMin, OMin),
#     ]
#
#     faces = [
#         (0, 1, 2, 3),
#         (4, 7, 6, 5),
#         (0, 4, 5, 1),
#         (1, 5, 6, 2),
#         (2, 6, 7, 3),
#         (4, 0, 3, 7),
#     ]
#
#     return verts, faces

#

# class OBJECT_OT_add_diamond_collision(Operator, AddObjectHelper):
#     """Create a new Mesh Object"""
#     bl_idname = "mesh.add_diamond_collision"
#     bl_label = "Add Diamond Collision"
#     bl_options = {'REGISTER', 'UNDO'}
#
#     # scale: FloatVectorProperty(
#     #     name="scale",
#     #     default=(1.0, 1.0, 1.0),
#     #     subtype='TRANSLATION',
#     #     description="scaling",
#     # )
#
#     def execute(self, context):
#         verts_loc, faces = add_diamond(context)
#         add_box_from_vertex_face_data(self, context,verts_loc, faces)
#
#         return {'FINISHED'}


# def add_object_button(self, context):
#     self.layout.operator(
#         OBJECT_OT_add_object.bl_idname,
#         text="Add Object",
#         icon='PLUGIN')


# # This allows you to right click on a button and link to documentation
# def add_object_manual_map():
#     url_manual_prefix = "https://docs.blender.org/manual/en/latest/"
#     url_manual_mapping = (
#         ("bpy.ops.mesh.add_object", "scene_layout/object/types.html"),
#     )
#     return url_manual_prefix, url_manual_mapping
