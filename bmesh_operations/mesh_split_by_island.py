import bpy
import bmesh


# Simple - get all linked faces
def get_linked_faces(f):
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
    # this is more involved, as we have to remap the new index
    # to do this, we reconstruct a new vert list and only append new items to it
    dic={}
    py_verts = []
    py_faces = []

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

    # print(py_verts, py_faces)
    dic['py_verts'] = py_verts
    dic['py_faces'] = py_faces

    return dic
def get_face_islands(bm, faces, face_islands = [], i=0):
    if len(faces) == 0 or i > 10:
        return face_islands
    else:
        bm.faces.ensure_lookup_table()
        #print('FACES ' + str(len(faces)))

        linked_faces = get_linked_faces(faces[0])
        #print('LINKED FACES ' + str(len(linked_faces)))
        face_islands.append(construct_python_faces(linked_faces))

        remaining_faces = [face for face in faces if face not in linked_faces]
        #print('REMAINING FACES ' + str(len(remaining_faces)))

        i = i + 1
        islands = get_face_islands(bm, remaining_faces, face_islands, i)

        return islands



def create_objs_from_island(obj, use_world = True):
    wld_mat = obj.matrix_world

    # change mode to editmode
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

        name = 'Object'
        me = bpy.data.meshes.new(name)
        if use_world:
            me.from_pydata([wld_mat @ x_co for x_co in py_verts], [], py_faces)
        else:
            me.from_pydata([x_co for x_co in py_verts], [], py_faces)

        # create a new object, and link it to the current view layer for display
        ob = bpy.data.objects.new(name='output', object_data=me)
        ob.select_set(False)
        #bpy.context.view_layer.active_layer_collection.collection.objects.link(ob)
        objs.append(ob)
    
    return objs




