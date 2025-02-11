import bmesh
import bpy


def bmesh_join(list_of_bmeshes, list_of_matrices, normal_update=False):
    """
    Merge multiple BMesh objects into a single BMesh, with optional normal updates.

    Parameters:
    list_of_bmeshes (list of bmesh.types.BMesh): List of BMesh objects to be merged.
    list_of_matrices (list of mathutils.Matrix): List of transformation matrices corresponding to each BMesh object.
    normal_update (bool, optional): If True, update the normals of the resulting BMesh. Defaults to False.

    Returns:
    bpy.types.Mesh: A new Blender Mesh object containing the merged BMesh data.
    """

    bm = bmesh.new()
    add_vert = bm.verts.new
    add_face = bm.faces.new
    add_edge = bm.edges.new

    for bm_to_add, matrix in zip(list_of_bmeshes, list_of_matrices):
        bm_to_add.transform(matrix)

    for bm_to_add in list_of_bmeshes:
        offset = len(bm.verts)

        for v in bm_to_add.verts:
            add_vert(v.co)

        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        if bm_to_add.faces:
            for face in bm_to_add.faces:
                try:
                    add_face(tuple(bm.verts[i.index + offset] for i in face.verts))
                except:
                    pass
            bm.faces.index_update()

        if bm_to_add.edges:
            for edge in bm_to_add.edges:
                edge_seq = tuple(bm.verts[i.index + offset]
                                 for i in edge.verts)
                try:
                    add_edge(edge_seq)
                except ValueError:
                    # edge exists!
                    pass
            bm.edges.index_update()

    if normal_update:
        bm.normal_update()

    me = bpy.data.meshes.new("joined_mesh")
    bm.to_mesh(me)

    return me

def delete_non_selected_verts(obj):
    # Create a BMesh from the object's mesh data
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Select non-selected vertices
    non_selected_verts = [v for v in bm.verts if not v.select]

    # Remove non-selected vertices
    bmesh.ops.delete(bm, geom=non_selected_verts, context='VERTS')

    # Write the updated BMesh back to the mesh
    bm.to_mesh(obj.data)
    bm.free()

    # Update the mesh to reflect changes
    obj.data.update()

    return obj

