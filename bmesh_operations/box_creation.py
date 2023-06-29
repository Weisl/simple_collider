import bmesh
import bpy

from bpy_extras.object_utils import object_data_add


tmp_name = 'box_collider'

# vertex indizes defining the faces of the cube
face_order = [
    (0, 1, 2, 3),
    (4, 7, 6, 5),
    (0, 4, 5, 1),
    (1, 5, 6, 2),
    (2, 6, 7, 3),
    (4, 0, 3, 7),
]


def add_box_object(context, vertices):
    """Generate a new object from the given vertices"""

    global tmp_name

    verts = vertices
    edges = []
    faces = [[0, 1, 2, 3], [7, 6, 5, 4], [5, 6, 2, 1], [0, 3, 7, 4], [3, 2, 6, 7], [4, 5, 1, 0]]

    mesh = bpy.data.meshes.new(name=tmp_name)
    mesh.from_pydata(verts, edges, faces)

    return object_data_add(context, mesh, operator=None, name=None)


def verts_faces_to_bbox_collider(self, context, verts_loc):
    """Create box collider for selected mesh area in edit mode"""

    global tmp_name

    # add new mesh
    mesh = bpy.data.meshes.new(tmp_name)
    bm = bmesh.new()

    # create mesh vertices
    for v_co in verts_loc:
        bm.verts.new(v_co)

    # connect vertices to faces
    bm.verts.ensure_lookup_table()
    for f_idx in face_order:
        bm.faces.new([bm.verts[i] for i in f_idx])

    # update bmesh to draw properly in viewport
    bm.to_mesh(mesh)
    mesh.update()

    # create new object from mesh and link it to collection
    new_collider = bpy.data.objects.new(tmp_name, mesh)

    root_collection = context.scene.collection
    root_collection.objects.link(new_collider)

    return new_collider