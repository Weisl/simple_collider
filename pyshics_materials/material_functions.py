import bpy
import bmesh
import random

def create_material(name, diffuse, fakeUser=True):
    '''Create a materials if none with the specified name already exists'''
    for mat in bpy.data.materials:
        if mat.name == name:
            if fakeUser == True:
                mat.use_fake_user = True
            return mat

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = diffuse
    mat.isPhysicsMaterial = True

    if fakeUser == True:
        mat.use_fake_user = True

    return mat

def set_material(ob, mat):
    '''Assign material to object'''
    # add material to object
    me = ob.data
    me.materials.append(mat)


def remove_materials(obj):
    '''Remove all materials from object'''
    if obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']:
        obj.data.materials.clear()


def create_default_material():
    '''Create a default material'''
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences

    if prefs:
        default_mat_name = prefs.physics_material_name

        if not default_mat_name:
            default_mat_name = 'COL_DEFAULT'

        if default_mat_name and default_mat_name in bpy.data.materials:
            default_material = bpy.data.materials[default_mat_name]
        else:
            default_material = create_material(default_mat_name, (0.0, 0.5, 1, 0.5))
    else:
        default_mat_name = 'COL_DEFAULT'
        default_material = create_material(default_mat_name, (0.0, 0.5, 1, 0.5))

    return default_material

def create_physics_material(physics_material_name):
    '''Create a default material'''
    if physics_material_name and physics_material_name in bpy.data.materials:
        physic_material = bpy.data.materials[physics_material_name]
    else:
        physic_material = create_default_material()

    return physic_material


# Materials
def assign_physics_material(object, physics_material_name):
    '''Remove existing materials from an object and assign the physics material'''
    if object.mode == 'EDIT':
        me = object.data
        mat = bpy.data.materials[physics_material_name]

        if mat.name not in me.materials:
            me.materials.append(mat)
        matList = object.material_slots
        matIdx = matList[mat.name].slot_index

        bm = bmesh.from_edit_mesh(object.data)  # Create bmesh object from object mesh

        for face in bm.faces:  # Iterate over all of the object's faces
            if face.select == True:
                face.material_index = matIdx

        object.data.update()  # Update the mesh from the bmesh data

    elif object.mode == 'OBJECT':
        remove_materials(object)
        mat = create_physics_material(physics_material_name)
        set_material(object, mat)
    else:
        bpy.ops.object.mode_set(mode='OBJECT')
        remove_materials(object)
        mat = create_physics_material(physics_material_name)
        set_material(object, mat)

def set_default_active_mat():
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    default_mat_name = prefs.physics_material_name

    mat = bpy.data.materials.get(default_mat_name, create_default_material())
    bpy.context.scene.active_physics_material = mat



def set_active_physics_material(context, physics_material_name):
    ''' '''
    context.scene.active_physics_material = bpy.data.materials[physics_material_name]