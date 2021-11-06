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
        for i in range(0, len(obj.material_slots)):
            obj.active_material_index = i
            bpy.ops.object.material_slot_remove()
            # print ("entered")


def set_material(ob, mat):
    '''Assign material to object'''
    # add material to object
    me = ob.data
    me.materials.append(mat)
