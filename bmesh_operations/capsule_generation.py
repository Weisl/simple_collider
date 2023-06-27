import math
import bmesh

# Function to calculate the distance between two points
def distance(p1, p2):
    return math.sqrt(sum((p1[i] - p2[i]) ** 2 for i in range(len(p1))))

# Function to calculate the distance between a point and a line segment
def point_line_segment_distance(p, p1, p2):
    v = [p2[i] - p1[i] for i in range(len(p1))]
    w = [p[i] - p1[i] for i in range(len(p1))]

    t = max(0, min(1, sum(w[i] * v[i] for i in range(len(v))) / sum(v[i] * v[i] for i in range(len(v)))))
    closest_point = [p1[i] + t * v[i] for i in range(len(p1))]
    return distance(p, closest_point)

# Function to calculate the radius and height of the bounding capsule
def calculate_radius_height(points):
    max_distance = 0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            d = distance(points[i], points[j])
            if d > max_distance:
                max_distance = d

    radius = max_distance / 2
    height = max_distance - radius
    return radius, height

@staticmethod
def create_capsule(longitudes=32, latitudes=16, rings=0, depth=1.0, radius=0.5, uv_profile="FIXED"):

    # Validate arguments.
    verif_rad = max(0.0001, radius)
    verif_depth = max(0.0002, depth)
    verif_rings = max(0, rings)
    verif_lons = max(3, longitudes)

    # Latitudes must be even so that equators can be split.
    verif_lats = max(2, latitudes)
    if (verif_lats % 2) != 0:
        verif_lats += 1

    # Preliminary calculations.
    calc_middle = verif_rings > 0
    half_lats = verif_lats // 2
    half_lats_n1 = half_lats - 1
    half_lats_n2 = half_lats - 2
    verif_rings_p1 = verif_rings + 1
    verif_lons_p1 = verif_lons + 1
    v_lons_half_lat_n1 = half_lats_n1 * verif_lons
    v_lons_v_sections_p1 = verif_rings_p1 * verif_lons
    half_depth = verif_depth * 0.5
    summit = half_depth + verif_rad

    # Coordinate index offsets.
    idx_v_n_equator = verif_lons_p1 + verif_lons * half_lats_n2
    idx_v_cyl = idx_v_n_equator + verif_lons
    idx_v_s_equator = (idx_v_cyl + verif_lons * verif_rings) \
        if calc_middle else idx_v_cyl
    idx_v_south = idx_v_s_equator + verif_lons
    idx_v_south_cap = idx_v_south + verif_lons * half_lats_n2
    idx_v_south_pole = idx_v_south_cap + verif_lons

    # Texture coordinate index offsets.
    idx_vt_n_equator = verif_lons + verif_lons_p1 * half_lats_n1
    idx_vt_cyl = idx_vt_n_equator + verif_lons_p1
    idx_vt_s_equator = (idx_vt_cyl + verif_lons_p1 * verif_rings) \
        if calc_middle else idx_vt_cyl
    idx_vt_s_hemi = idx_vt_s_equator + verif_lons_p1
    idx_vt_s_polar = idx_vt_s_hemi + verif_lons_p1 * half_lats_n2
    idx_vt_s_cap = idx_vt_s_polar + verif_lons_p1

    # Normal index offsets.
    idx_vn_south = idx_v_n_equator + verif_lons
    idx_vn_south_cap = idx_vn_south + verif_lons * half_lats_n2
    idx_vn_south_pole = idx_vn_south_cap + verif_lons

    # Find index offsets for face indices.
    idx_fs_cyl = verif_lons + v_lons_half_lat_n1
    idx_fs_south_equat = idx_fs_cyl + v_lons_v_sections_p1
    idx_fs_south_hemi = idx_fs_south_equat + v_lons_half_lat_n1

    # List lengths.
    len_vs = idx_v_south_pole + 1
    len_vts = idx_vt_s_cap + verif_lons
    len_vns = idx_vn_south_pole + verif_lons
    len_indices = idx_fs_south_hemi + verif_lons

    # Allocate mesh data.
    vs = [(0.0, 0.0, 0.0)] * len_vs
    vts = [(0.5, 0.5)] * len_vts
    vns = [(0.0, 0.0, 1.0)] * len_vns

    # Allocate indices arrays. (When properly filled, index tuples at the
    # poles will be of length 3, else of length 4.)
    v_indices = [(0, 0, 0)] * len_indices
    vt_indices = [(0, 0, 0)] * len_indices
    vn_indices = [(0, 0, 0)] * len_indices

    # Ranges for loops.
    lons_range = range(0, verif_lons)
    lons_p1_range = range(0, verif_lons_p1)
    hemi_range = range(0, half_lats_n1)

    # Set poles.
    vs[0] = (0.0, 0.0, summit)
    vs[idx_v_south_pole] = (0.0, 0.0, -summit)

    vns[0] = (0.0, 0.0, 1.0)
    vns[idx_vn_south_pole] = (0.0, 0.0, -1.0)

    # Calculate polar texture coordinates. UVs form a triangle at the poles,
    # where the polar vertex is centered between the other two vertices.
    # That is why j is offset by 0.5 . There is one fewer column of UVs at
    # the poles, so the for loop uses the coordinate longitude range.
    to_theta = math.tau / verif_lons
    to_phi = math.pi / verif_lats
    to_tex_horizontal = 1.0 / verif_lons
    to_tex_vertical = 1.0 / half_lats
    sin_cos_theta_cache = [(0.0, 1.0)] * verif_lons

    for j in lons_range:
        j_next_vt = j + 1
        j_next_v = j_next_vt % verif_lons

        # Polar to Cartesian coordinates.
        theta = j * to_theta
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        sin_cos_theta_cache[j] = (sin_theta, cos_theta)

        # Texture coordinates at North and South poles.
        s_tex = (j + 0.5) * to_tex_horizontal
        vts[j] = (s_tex, 1.0)
        vts[idx_vt_s_cap + j] = (s_tex, 0.0)

        # Multiply by radius to get equatorial x and y.
        x = verif_rad * cos_theta
        y = verif_rad * sin_theta

        # Equatorial coordinates.
        vs[idx_v_n_equator + j] = (x, y, half_depth)
        vs[idx_v_s_equator + j] = (x, y, -half_depth)

        # Equatorial normals.
        vns[idx_v_n_equator + j] = (cos_theta, sin_theta, 0.0)

        # North triangle fan.
        v_indices[j] = (0, j_next_vt, 1 + j_next_v)
        vt_indices[j] = (j, verif_lons + j, verif_lons + j_next_vt)
        vn_indices[j] = (0, j_next_vt, 1 + j_next_v)

        # South triangle fan.
        v_indices[idx_fs_south_hemi + j] = (
            idx_v_south_pole,
            idx_v_south_cap + j_next_v,
            idx_v_south_cap + j)

        vt_indices[idx_fs_south_hemi + j] = (
            idx_vt_s_cap + j,
            idx_vt_s_polar + j_next_vt,
            idx_vt_s_polar + j)

        vn_indices[idx_fs_south_hemi + j] = (
            idx_vn_south_pole,
            idx_vn_south_cap + j_next_v,
            idx_vn_south_cap + j)

    # Calculate equatorial texture coordinates. Cache horizontal measure.
    s_tex_cache = [0.5] * verif_lons_p1

    # Aspect ratio.
    vt_aspect_south = 1.0 / 3.0
    if uv_profile == "ASPECT":
        vt_aspect_south = (verif_rad / (verif_depth + 2.0 * verif_rad))
    elif uv_profile == "UNIFORM":
        vt_aspect_south = half_lats / (verif_rings_p1 + verif_lats)
    vt_aspect_north = 1.0 - vt_aspect_south

    for j in lons_p1_range:
        s_tex = j * to_tex_horizontal
        s_tex_cache[j] = s_tex
        vts[idx_vt_n_equator + j] = (s_tex, vt_aspect_north)
        vts[idx_vt_s_equator + j] = (s_tex, vt_aspect_south)

    # Divide latitudes into hemispheres. Start at i = 1 due to the poles.
    v_hemi_offset_north = 1
    v_hemi_offset_south = idx_v_south

    vt_hemi_offset_north = verif_lons
    vt_hemi_offset_south = idx_vt_s_hemi

    vn_hemi_offset_south = idx_vn_south

    f_hemi_offset_north = verif_lons
    f_hemi_offset_south = idx_fs_south_equat

    for i in hemi_range:
        ip1 = i + 1.0
        phi = ip1 * to_phi
        i_v_lons = i * verif_lons

        # Symmetries mean cos and sin only need to be called once.
        sin_phi_south = math.sin(phi)
        cos_phi_south = math.cos(phi)
        sin_phi_north = -cos_phi_south
        cos_phi_north = sin_phi_south

        # North coordinates: multiply by radius and offset.
        rho_cos_phi_north = verif_rad * cos_phi_north
        rho_sin_phi_north = verif_rad * sin_phi_north
        offset_z_north = half_depth - rho_sin_phi_north

        # South coordinates: multiply by radius and offset.
        rho_cos_phi_south = verif_rad * cos_phi_south
        rho_sin_phi_south = verif_rad * sin_phi_south
        offset_z_south = -half_depth - rho_sin_phi_south

        # North coordinate index offset.
        v_curr_lat_n = 1 + i_v_lons
        v_next_lat_n = v_curr_lat_n + verif_lons

        # North texture coordinate index offset.
        vt_curr_lat_n = verif_lons + i * verif_lons_p1
        vt_next_lat_n = vt_curr_lat_n + verif_lons_p1

        # North normal index offset.
        vn_curr_lat_n = 1 + i_v_lons
        vn_next_lat_n = vn_curr_lat_n + verif_lons

        # South coordinate index offset.
        v_curr_lat_s = idx_v_s_equator + i_v_lons
        v_next_lat_s = v_curr_lat_s + verif_lons

        # South texture coordinate index offset.
        vt_curr_lat_s = idx_vt_s_equator + i * verif_lons_p1
        vt_next_lat_s = vt_curr_lat_s + verif_lons_p1

        # South normal index offset.
        vn_curr_lat_s = idx_v_n_equator + i_v_lons
        vn_next_lat_s = vn_curr_lat_s + verif_lons

        # Coordinates & normals.
        for j in lons_range:
            j_next_vt = j + 1
            j_next_v = j_next_vt % verif_lons
            sin_theta, cos_theta = sin_cos_theta_cache[j]

            # North coordinate.
            vs[v_hemi_offset_north] = (
                rho_cos_phi_north * cos_theta,
                rho_cos_phi_north * sin_theta,
                offset_z_north)

            # South coordinate.
            vs[v_hemi_offset_south] = (
                rho_cos_phi_south * cos_theta,
                rho_cos_phi_south * sin_theta,
                offset_z_south)

            # North normal.
            vns[v_hemi_offset_north] = (
                cos_phi_north * cos_theta,
                cos_phi_north * sin_theta,
                -sin_phi_north)

            # South normal.
            vns[vn_hemi_offset_south] = (
                cos_phi_south * cos_theta,
                cos_phi_south * sin_theta,
                -sin_phi_south)

            # Update vertex offsets.
            v_hemi_offset_north += 1
            v_hemi_offset_south += 1
            vn_hemi_offset_south += 1

            # Coordinates North quad.
            v_indices[f_hemi_offset_north] = (
                v_curr_lat_n + j,
                v_next_lat_n + j,
                v_next_lat_n + j_next_v,
                v_curr_lat_n + j_next_v)

            # Texture coordinates North quad.
            vt_indices[f_hemi_offset_north] = (
                vt_curr_lat_n + j,
                vt_next_lat_n + j,
                vt_next_lat_n + j_next_vt,
                vt_curr_lat_n + j_next_vt)

            # Normals North quad.
            vn_indices[f_hemi_offset_north] = (
                vn_curr_lat_n + j,
                vn_next_lat_n + j,
                vn_next_lat_n + j_next_v,
                vn_curr_lat_n + j_next_v)

            # Coordinates South quad.
            v_indices[f_hemi_offset_south] = (
                v_curr_lat_s + j,
                v_next_lat_s + j,
                v_next_lat_s + j_next_v,
                v_curr_lat_s + j_next_v)

            # Texture coordinates South quad.
            vt_indices[f_hemi_offset_south] = (
                vt_curr_lat_s + j,
                vt_next_lat_s + j,
                vt_next_lat_s + j_next_vt,
                vt_curr_lat_s + j_next_vt)

            # Normals South quad.
            vn_indices[f_hemi_offset_south] = (
                vn_curr_lat_s + j,
                vn_next_lat_s + j,
                vn_next_lat_s + j_next_v,
                vn_curr_lat_s + j_next_v)

            # Update face index offsets.
            f_hemi_offset_north += 1
            f_hemi_offset_south += 1

        # Find vertical component of texture.
        t_tex_fac = ip1 * to_tex_vertical
        t_tex_north = 1.0 * (1.0 - t_tex_fac) + t_tex_fac * vt_aspect_north
        t_tex_south = vt_aspect_south * (1.0 - t_tex_fac) + t_tex_fac * 0.0

        # Texture coordinates.
        for j in lons_p1_range:
            s_tex = s_tex_cache[j]

            vts[vt_hemi_offset_north] = (s_tex, t_tex_north)
            vts[vt_hemi_offset_south] = (s_tex, t_tex_south)

            vt_hemi_offset_north += 1
            vt_hemi_offset_south += 1

    # Calculate rings of cylinder in middle.
    if calc_middle:

        # Linear interpolation must exclude the origin (North equator) and
        # destination (South equator), so step must not equal 0.0 or 1.0.
        to_fac = 1.0 / verif_rings_p1
        v_cyl_offset = idx_v_cyl
        vt_cyl_offset = idx_vt_cyl

        for m in range(1, verif_rings_p1):

            fac = m * to_fac
            cmpl_fac = 1.0 - fac
            t_tex = vt_aspect_north * cmpl_fac + vt_aspect_south * fac

            # Coordinates.
            for j in lons_range:

                # The x and y coordinates should be the same. North z should
                # be half_depth while South z should be -half_depth. So lerp
                # between these is not strictly necessary.
                v_equator_north = vs[idx_v_n_equator + j]
                v_equator_south = vs[idx_v_s_equator + j]
                vs[v_cyl_offset] = (
                    v_equator_north[0] * cmpl_fac +
                    v_equator_south[0] * fac,
                    v_equator_north[1] * cmpl_fac +
                    v_equator_south[1] * fac,
                    v_equator_north[2] * cmpl_fac +
                    v_equator_south[2] * fac)
                v_cyl_offset += 1

            # Texture coordinates.
            for j in lons_p1_range:
                s_tex = s_tex_cache[j]
                vts[vt_cyl_offset] = (s_tex, t_tex)
                vt_cyl_offset += 1

    # Cylinder indices (quads).
    f_cyl_offset = idx_fs_cyl
    for m in range(0, verif_rings_p1):

        v_curr_ring = idx_v_n_equator + m * verif_lons
        v_next_ring = v_curr_ring + verif_lons

        vt_curr_ring = idx_vt_n_equator + m * verif_lons_p1
        vt_next_ring = vt_curr_ring + verif_lons_p1

        for j in lons_range:
            j_next_vt = j + 1
            j_next_v = j_next_vt % verif_lons

            # Coordinate quad.
            v_indices[f_cyl_offset] = (
                v_curr_ring + j,
                v_next_ring + j,
                v_next_ring + j_next_v,
                v_curr_ring + j_next_v)

            # Texture coordinate quad.
            vt_indices[f_cyl_offset] = (
                vt_curr_ring + j,
                vt_next_ring + j,
                vt_next_ring + j_next_vt,
                vt_curr_ring + j_next_vt)

            # Normals quad.
            vn_indices[f_cyl_offset] = (
                idx_v_n_equator + j,
                idx_v_n_equator + j,
                idx_v_n_equator + j_next_v,
                idx_v_n_equator + j_next_v)

            f_cyl_offset += 1

    # Return a dictionary containing data.
    return {"vs": vs,
            "vts": vts,
            "vns": vns,
            "v_indices": v_indices,
            "vt_indices": vt_indices,
            "vn_indices": vn_indices}

@staticmethod
def mesh_data_to_bmesh(
        vs, vts, vns,
        v_indices, vt_indices, vn_indices):

    bm = bmesh.new()

    # Create BM vertices.
    len_vs = len(vs)
    bm_verts = [None] * len_vs
    for i in range(0, len_vs):
        v = vs[i]
        bm_verts[i] = bm.verts.new(v)

    # Create BM faces.
    len_v_indices = len(v_indices)
    bm_faces = [None] * len_v_indices
    uv_layer = bm.loops.layers.uv.verify()

    for i in range(0, len_v_indices):
        v_loop = v_indices[i]
        vt_loop = vt_indices[i]
        vn_loop = vn_indices[i]

        # Find list of vertices per face.
        len_v_loop = len(v_loop)
        face_verts = [None] * len_v_loop
        for j in range(0, len_v_loop):
            face_verts[j] = bm_verts[v_loop[j]]

        # Create BM face.
        bm_face = bm.faces.new(face_verts)
        bm_faces[i] = bm_face
        bm_face_loops = list(bm_face.loops)

        # Assign texture coordinates and normals.
        for k in range(0, len_v_loop):
            bm_face_loop = bm_face_loops[k]
            bm_face_loop[uv_layer].uv = vts[vt_loop[k]]
            bm_face_loop.vert.normal = vns[vn_loop[k]]

    return bm