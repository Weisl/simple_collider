import bpy


def create_material(name, diffuse, fakeUser=True):
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


def set_material(ob, mat):
    '''Assign material to object'''
    # add material to object
    me = ob.data
    me.materials.append(mat)


def remove_materials(obj):
    if obj.type == 'MESH' or obj.type == 'CURVE' or obj.type == 'SURFACE' or obj.type == 'FONT' or obj.type == 'META':
        obj.data.materials.clear()


def create_default_material(physics_material_name):
    if physics_material_name and physics_material_name in bpy.data.materials:
        default_material = bpy.data.materials[physics_material_name]
    else:
        default_material = create_material('COL_DEFAULT', (1, 1, 1, 0.5))

    return default_material


# Materials
def set_physics_material(bounding_object, physics_material_name):
    remove_materials(bounding_object)

    mat = create_default_material(physics_material_name)
    set_material(bounding_object, mat)
