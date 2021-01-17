import bpy


def alignObjects(new, old):
    """Align two objects"""
    new.matrix_world = old.matrix_world


def get_bounding_box(obj):
    """returns the bounding box for an object"""
    return obj.bound_box


def set_origin_to_center_of_mass(context, ob):
    """"""
    oldActive = context.object
    context.view_layer.objects.active = ob

    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    context.view_layer.objects.active = oldActive


def add_displace_mod(obj, strenght):
    # add a displacement modifier to the object to inflate or shrink it
    modifier = obj.modifiers.new(name="ColliderOffset_disp", type='DISPLACE')
    modifier.strength = strenght
    return modifier