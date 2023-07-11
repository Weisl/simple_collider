from mathutils import Matrix, Vector

def get_sca_matrix(scale):
    """get scale matrix"""
    scale_mx = Matrix()
    for i in range(3):
        scale_mx[i][i] = scale[i]
    return scale_mx


def get_loc_matrix(location):
    """get location matrix"""
    return Matrix.Translation(location)


def get_rot_matrix(rotation):
    """get rotation matrix"""
    return rotation.to_matrix().to_4x4()
