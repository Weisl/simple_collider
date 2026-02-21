import bmesh
import bpy


def _get_linked_faces(f):
    """
    Iteratively retrieve all faces linked to the given face.

    Sets BMFace.tag = True on every face it visits; f must be untagged on entry.

    Parameters:
    f (bmesh.types.BMFace): The starting face from which to find all linked faces.

    Returns:
    list of bmesh.types.BMFace: A list of all faces linked to the starting face.
    """
    # Iterative DFS so that large islands do not hit Python's recursion limit
    # and avoid the O(N^2) list copying of a recursive extend()-based approach.
    stack = [f]
    f_linked = []
    while stack:
        f = stack.pop()
        if f.tag:
            continue
        f.tag = True
        f_linked.append(f)
        for e in f.edges:
            if len(e.link_faces) == 2:
                for nxt in e.link_faces:
                    if not nxt.tag:
                        stack.append(nxt)
    return f_linked


def construct_python_faces(bmesh_faces):
    """
    Construct a dictionary representation of the given BMesh faces with remapped indices.

    Parameters:
    bmesh_faces (list of bmesh.types.BMFace): A list of BMesh faces.

    Returns:
    dict: A dictionary containing the vertices, faces, and face material indices.
          - 'py_verts': List of vertex coordinates.
          - 'py_faces': List of faces, each face being a list of vertex indices.
          - 'py_face_mat': List of material indices for each face.
    """

    # this is more involved, as we have to remap the new index
    # to do this, we reconstruct a new vert list and only append new items to it
    dic = {}
    vert_index_map = {}  # BMVert -> index in py_verts
    py_verts = []
    py_faces = []
    py_face_mat = []

    for f in bmesh_faces:
        # cur_face_indices holds the new indices of our verts per face
        cur_face_indices = []

        for v in f.verts:
            if v not in vert_index_map:
                # this vert is found for the first time, add it
                vert_index_map[v] = len(py_verts)
                py_verts.append(v.co)

            # add the new index of the current vert to the current face index list
            cur_face_indices.append(vert_index_map[v])

        # face index list construction is complete, add it to the face list
        py_faces.append(cur_face_indices)
        py_face_mat.append(f.material_index)

    # print(py_verts, py_faces)
    dic['py_verts'] = py_verts
    dic['py_faces'] = py_faces
    dic['py_face_mat'] = py_face_mat

    return dic


def _get_face_islands(faces):
    """
    Retrieve all face islands (groups of connected faces) from the given faces.

    Uses _get_linked_faces() to traverse each island. As a side effect,
    _get_linked_faces() sets BMFace.tag = True on every face it visits, which
    is how already-processed faces are skipped on subsequent iterations.

    Parameters:
    faces (list of bmesh.types.BMFace): The list of faces to process.

    Returns:
    list: A list of dictionaries, each containing the vertices, faces, and face material indices for an island.
    """

    face_islands = []
    for face in faces:
        if not face.tag:
            linked_faces = _get_linked_faces(face)
            face_islands.append(construct_python_faces(linked_faces))

    return face_islands


def create_objs_from_island(obj, use_world=True):
    """
    Create separate objects from face islands of the given object.

    Parameters:
    obj (bpy.types.Object): The Blender object to process.
    use_world (bool, optional): If True, use the world matrix for transformations. Defaults to True.

    Returns:
    list of bpy.types.Object: A list of new objects created from the face islands.
    """

    wld_mat = obj.matrix_world

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    face_islands = _get_face_islands(bm.faces)
    bm.free()
    # print('Face Islands: ' + str(face_islands))
    objs = []

    for island in face_islands:
        py_verts = island['py_verts']
        py_faces = island['py_faces']
        py_face_mat = island['py_face_mat']

        name = 'Object'
        me = bpy.data.meshes.new(name)
        if use_world:
            me.from_pydata([wld_mat @ x_co for x_co in py_verts], [], py_faces)
        else:
            me.from_pydata([x_co for x_co in py_verts], [], py_faces)

        for f, f_mat_idx in zip(me.polygons, py_face_mat):
            f.material_index = f_mat_idx

        # create a new object, and link it to the current view layer for display
        ob = bpy.data.objects.new(name='output', object_data=me)
        ob.select_set(False)
        # bpy.context.view_layer.active_layer_collection.collection.objects.link(ob)
        objs.append(ob)

    return objs
