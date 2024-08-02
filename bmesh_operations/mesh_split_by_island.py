import sys

import bmesh
import bpy


# Simple - get all linked faces
def get_linked_faces(f):
    """
    Recursively retrieve all faces linked to the given face.

    Parameters:
    f (bmesh.types.BMFace): The starting face from which to find all linked faces.

    Returns:
    list of bmesh.types.BMFace: A list of all faces linked to the starting face.
    """

    sys.setrecursionlimit(10 ** 6)
    if f.tag:
        # If the face is already tagged, return empty list
        return []

    # Add the face to list that will be returned
    f_linked = [f]
    f.tag = True

    # Select edges that link two faces
    edges = [e for e in f.edges if len(e.link_faces) == 2]
    for e in edges:
        # Select all firs-degree linked faces, that are not yet tagged
        faces = [elem for elem in e.link_faces if not elem.tag]

        # Recursively call this function on all connected faces
        if not len(faces) == 0:
            for elem in faces:
                # Extend the list with second-degree connected faces
                f_linked.extend(get_linked_faces(elem))

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
    py_verts = []
    py_faces = []
    py_face_mat = []

    for f in bmesh_faces:
        # cur_face_indices holds the new indices of our verts per face
        cur_face_indices = []

        for v in f.verts:
            if v.co not in py_verts:
                # this vert is found for the first time, add it
                py_verts.append(v.co)

            # add the new index of the current vert to the current face index list
            cur_face_indices.append(py_verts.index(v.co))

        # face index list construction is complete, add it to the face list
        py_faces.append(cur_face_indices)
        py_face_mat.append(f.material_index)

    # print(py_verts, py_faces)
    dic['py_verts'] = py_verts
    dic['py_faces'] = py_faces
    dic['py_face_mat'] = py_face_mat

    return dic


def get_face_islands(bm, faces, face_islands=[], i=0):
    """
    Retrieve all face islands (groups of connected faces) from the given BMesh.

    Parameters:
    bm (bmesh.types.BMesh): The BMesh object.
    faces (list of bmesh.types.BMFace): The list of faces to process.
    face_islands (list, optional): The list to store face islands. Defaults to an empty list.
    i (int, optional): The current recursion depth. Defaults to 0.

    Returns:
    list: A list of dictionaries, each containing the vertices, faces, and face material indices for an island.
    """

    if len(faces) == 0:
        return face_islands
    else:
        bm.faces.ensure_lookup_table()

        linked_faces = get_linked_faces(faces[0])
        face_islands.append(construct_python_faces(linked_faces))

        remaining_faces = [face for face in faces if face not in linked_faces]

        i = i + 1
        islands = get_face_islands(bm, remaining_faces, face_islands, i)

        return islands


def create_objs_from_island(obj, use_world=True):
    """
    Create separate objects from face islands of the given object in edit mode.

    Parameters:
    obj (bpy.types.Object): The Blender object to process.
    use_world (bool, optional): If True, use the world matrix for transformations. Defaults to True.

    Returns:
    list of bpy.types.Object: A list of new objects created from the face islands.
    """

    wld_mat = obj.matrix_world

    # change mode to editmode
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    face_islands = []
    face_islands = get_face_islands(bm, bm.faces, face_islands)
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
