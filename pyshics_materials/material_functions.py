import bpy


def make_physics_material(name, diffuse, fakeUser=True):

    for mat in bpy.data.materials:
        if mat.name == name:
            if fakeUser == True:
                mat.use_fake_user = True
            return mat

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = diffuse
    if fakeUser == True:
        mat.use_fake_user = True

    return mat


def remove_materials(obj):
    if obj.type == 'MESH' or obj.type == 'CURVE' or obj.type == 'SURFACE' or obj.type == 'FONT' or obj.type == 'META':
        obj.data.materials.clear()


def set_material(ob, mat):
    '''Assign material to object'''
    # add material to object
    me = ob.data
    me.materials.append(mat)
