import bmesh
import numpy as np
from collections import deque

# Hard cap on cells per axis. The occupancy grid, flood-fill and greedy-mesh
# passes are plain Python loops over the grid, so this bounds worst-case time
# when a user drags voxel size down to something tiny relative to the object.
MAX_GRID_AXIS_CELLS = 48

# Each of the 3 possible ramp planes as (a_axis, b_axis, e_axis): the cut is
# made in the (a, b) cross-section and the wedge is extruded along e.
RAMP_PLANES = ((0, 2, 1), (0, 1, 2), (1, 2, 0))

DIRECTIONS = ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1))


def mesh_max_dimension(mesh):
    """Local-space bounding box max extent, for sizing voxel_size relative to the mesh."""
    if len(mesh.vertices) == 0:
        return 0.0
    coords = np.empty((len(mesh.vertices), 3), dtype=np.float64)
    mesh.vertices.foreach_get('co', coords.ravel())
    return float(np.max(coords.max(axis=0) - coords.min(axis=0)))


def _mesh_local_triangles(mesh):
    """Return (Nx3 float64 local-space vertex coords, Mx3 int64 triangle vertex indices)."""
    mesh.calc_loop_triangles()

    verts = np.empty((len(mesh.vertices), 3), dtype=np.float64)
    if len(mesh.vertices):
        mesh.vertices.foreach_get('co', verts.ravel())

    tris = np.empty((len(mesh.loop_triangles), 3), dtype=np.int64)
    if len(mesh.loop_triangles):
        mesh.loop_triangles.foreach_get('vertices', tris.ravel())

    return verts, tris


def _clamped_voxel_size(bbox_min, bbox_max, voxel_size, padding):
    """Coarsen voxel_size if it would push the grid past MAX_GRID_AXIS_CELLS."""
    max_extent = float(np.max(bbox_max - bbox_min))
    if max_extent <= 0.0:
        return voxel_size
    usable_cells = max(MAX_GRID_AXIS_CELLS - 2 * padding, 1)
    min_voxel_size = max_extent / usable_cells
    return max(voxel_size, min_voxel_size)


def _grid_dims_and_origin(bbox_min, bbox_max, voxel_size, padding):
    """Grid cell counts per axis, and the world position of cell (0, 0, 0).

    Rounds each axis to the *nearest* whole number of cells rather than
    always up, then centers that core region on the mesh's bbox. Any leftover
    slack (or shortfall) from the rounding is split evenly between the two
    sides -- so the grid hugs the source surface as closely as possible
    instead of always growing outward to guarantee full containment.
    """
    size = bbox_max - bbox_min
    core_cells = np.maximum(np.round(size / voxel_size).astype(int), 1)
    dims = np.minimum(core_cells + 2 * padding, MAX_GRID_AXIS_CELLS)
    slack = core_cells * voxel_size - size
    origin = bbox_min - padding * voxel_size - slack / 2
    return tuple(int(d) for d in dims), origin


def _mark_triangle(occupancy, origin, voxel_size, threshold, v0, v1, v2, max_depth=6):
    """Rasterize a triangle into the occupancy grid via its (subdivided) AABB.

    Large triangles are recursively split at their edge midpoints until each
    piece's AABB is within `threshold` of a single cell, then the whole AABB
    of the small piece is marked. This avoids a full triangle/box SAT test at
    the cost of being conservative (a few extra cells around thin/steep
    triangles) -- acceptable for a simplified collider.
    """
    dims = np.array(occupancy.shape)
    inv = 1.0 / voxel_size
    eps = voxel_size * 1e-4

    # Used only to resolve the "flat on a grid line" case below -- computed
    # once from the whole (undivided) triangle since every recursive piece
    # stays coplanar with it.
    normal = np.cross(v1 - v0, v2 - v0)

    stack = [(v0, v1, v2, 0)]

    while stack:
        a, b, c, depth = stack.pop()
        tri_min = np.minimum(np.minimum(a, b), c)
        tri_max = np.maximum(np.maximum(a, b), c)

        if depth < max_depth and np.max(tri_max - tri_min) > threshold:
            ab = (a + b) * 0.5
            bc = (b + c) * 0.5
            ca = (c + a) * 0.5
            stack.append((a, ab, ca, depth + 1))
            stack.append((ab, b, bc, depth + 1))
            stack.append((ca, bc, c, depth + 1))
            stack.append((ab, bc, ca, depth + 1))
            continue

        rel_min = (tri_min - origin) * inv
        rel_max = (tri_max - origin) * inv
        # "Belongs to the cell above" and "belongs to the cell below" readings
        # of the piece's span. These agree for any ordinary span; they can
        # only disagree (lo > hi) when the piece is flat exactly on a grid
        # line along that axis -- which is guaranteed at the mesh's own
        # bounding-box extremes, since the grid origin is defined from
        # bbox_min in exact voxel-size steps. Marking both cells there is
        # what pushes the whole collider outward by up to one voxel around
        # every flat, grid-aligned face (e.g. any box-like source mesh).
        lo = np.floor(rel_min + eps).astype(int)
        hi = np.ceil(rel_max - eps).astype(int) - 1

        flat = lo > hi
        if flat.any():
            # The face normal says which side the solid is actually on, so
            # collapse to that single, correct cell instead of both.
            for axis in np.nonzero(flat)[0]:
                n = normal[axis]
                if n > 1e-12:
                    lo[axis] = hi[axis]
                elif n < -1e-12:
                    hi[axis] = lo[axis]
                else:
                    # Orientation inconclusive for this axis (e.g. a sliver
                    # piece) -- fall back to the old, always-safe span.
                    lo[axis], hi[axis] = hi[axis], lo[axis]

        i0 = np.clip(lo, 0, dims - 1)
        i1 = np.clip(hi, 0, dims - 1)
        occupancy[i0[0]:i1[0] + 1, i0[1]:i1[1] + 1, i0[2]:i1[2] + 1] = True


def _voxelize_surface(verts_local, tris, origin, voxel_size, dims):
    occupancy = np.zeros(dims, dtype=bool)
    threshold = voxel_size * 0.75
    for tri in tris:
        _mark_triangle(occupancy, origin, voxel_size, threshold,
                       verts_local[tri[0]], verts_local[tri[1]], verts_local[tri[2]])
    return occupancy


def _flood_fill_outside(surface):
    """BFS from the grid boundary through non-surface cells.

    Anything unreached (enclosed interior cells, plus the surface cells
    themselves) ends up filled -- this is what makes the result watertight
    even when the source mesh isn't a perfectly closed manifold.
    """
    nx, ny, nz = surface.shape
    outside = np.zeros_like(surface)
    queue = deque()

    def try_add(idx):
        if surface[idx] or outside[idx]:
            return
        outside[idx] = True
        queue.append(idx)

    for i in range(nx):
        for j in range(ny):
            try_add((i, j, 0))
            try_add((i, j, nz - 1))
    for i in range(nx):
        for k in range(nz):
            try_add((i, 0, k))
            try_add((i, ny - 1, k))
    for j in range(ny):
        for k in range(nz):
            try_add((0, j, k))
            try_add((nx - 1, j, k))

    neighbors = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while queue:
        i, j, k = queue.popleft()
        for di, dj, dk in neighbors:
            ni, nj, nk = i + di, j + dj, k + dk
            if 0 <= ni < nx and 0 <= nj < ny and 0 <= nk < nz:
                try_add((ni, nj, nk))

    return outside


def _in_bounds(idx, dims):
    return 0 <= idx[0] < dims[0] and 0 <= idx[1] < dims[1] and 0 <= idx[2] < dims[2]


def _compute_face_availability(filled, diagonal_fill):
    """For every filled cell and each of the 6 face directions, decide whether
    a flat square face may be generated there by the greedy mesher.

    Cube cells: all 6 directions available.
    Ramp cells (diagonal_fill only): a ramp chamfers one convex corner of the
    cell with a single 45-degree cut. Of its 6 faces, 2 (perpendicular to the
    extrusion axis) become triangular end caps handled separately, 2 (the
    corner being cut away) disappear entirely, and the remaining 2 stay full
    squares and go through the same greedy pass as cubes.
    """
    dims = filled.shape

    if not diagonal_fill:
        avail = np.repeat(filled[..., np.newaxis], 6, axis=3)
        return avail, {}

    avail = np.zeros(dims + (6,), dtype=bool)
    ramp_info = {}

    def dir_index(axis, sign):
        return 2 * axis + (0 if sign > 0 else 1)

    for i, j, k in np.argwhere(filled):
        i, j, k = int(i), int(j), int(k)
        cell = (i, j, k)
        candidates = []

        for a_axis, b_axis, e_axis in RAMP_PLANES:
            for sa in (1, -1):
                for sb in (1, -1):
                    na = [i, j, k]; na[a_axis] += sa
                    nb = [i, j, k]; nb[b_axis] += sb
                    nd = [i, j, k]; nd[a_axis] += sa; nd[b_axis] += sb

                    if not _in_bounds(na, dims) or filled[tuple(na)]:
                        continue
                    if not _in_bounds(nb, dims) or filled[tuple(nb)]:
                        continue
                    if not _in_bounds(nd, dims) or filled[tuple(nd)]:
                        continue
                    candidates.append((a_axis, b_axis, e_axis, sa, sb))

        if len(candidates) == 1:
            a_axis, b_axis, e_axis, sa, sb = candidates[0]
            ramp_info[cell] = (a_axis, b_axis, e_axis, sa, sb)
            avail[i, j, k, dir_index(a_axis, -sa)] = True
            avail[i, j, k, dir_index(b_axis, -sb)] = True
        else:
            avail[i, j, k, :] = True

    return avail, ramp_info


def _emit_quad(bm, origin, voxel_size, axis, plane_idx, ax_b, b0, ax_c, c0):
    def make_point(b_coord, c_coord):
        p = [0.0, 0.0, 0.0]
        p[axis] = origin[axis] + plane_idx * voxel_size
        p[ax_b] = origin[ax_b] + b_coord * voxel_size
        p[ax_c] = origin[ax_c] + c_coord * voxel_size
        return tuple(p)

    verts = [bm.verts.new(make_point(b, c)) for b, c in
            ((b0, c0), (b0 + 1, c0), (b0 + 1, c0 + 1), (b0, c0 + 1))]
    try:
        bm.faces.new(verts)
    except ValueError:
        pass


def _add_cell_quads(bm, filled, avail_dir, origin, voxel_size, axis, sign):
    """Emit one quad per exposed cell face (no merging).

    Rectangles are *not* greedily merged across cells here -- doing so at
    this stage risks T-junctions (an edge on a big merged quad with no
    matching edge on an adjacent, differently-subdivided face, e.g. next to
    a ramp cell's own diagonal/cap geometry, or simply between differently
    sized merges on perpendicular faces of an irregular blob). Instead every
    quad aligns exactly with the grid, guaranteeing shared edges everywhere,
    and `bmesh.ops.dissolve_limited` safely collapses the coplanar interior
    edges afterwards -- Blender's own implementation, not a hand-rolled one.
    """
    dims = filled.shape
    neighbor_filled = np.zeros(dims, dtype=bool)

    src = [slice(None)] * 3
    dst = [slice(None)] * 3
    if sign > 0:
        src[axis] = slice(1, None)
        dst[axis] = slice(0, -1)
    else:
        src[axis] = slice(0, -1)
        dst[axis] = slice(1, None)
    neighbor_filled[tuple(dst)] = filled[tuple(src)]

    exposed = filled & avail_dir & (~neighbor_filled)
    if not exposed.any():
        return

    ax_b, ax_c = (a for a in range(3) if a != axis)

    for layer in range(dims[axis]):
        sl = [slice(None)] * 3
        sl[axis] = layer
        mask2d = exposed[tuple(sl)]
        if not mask2d.any():
            continue

        plane_coord = layer + (1 if sign > 0 else 0)
        for b0, c0 in np.argwhere(mask2d):
            _emit_quad(bm, origin, voxel_size, axis, plane_coord, ax_b, int(b0), ax_c, int(c0))


def _emit_ramp_cell(bm, origin, voxel_size, cell, a_axis, b_axis, e_axis, sa, sb,
                    cap_min, cap_max, stitch_min, stitch_max):
    i, j, k = cell
    idx = [i, j, k]

    def make_point(u, v, e):
        p = [0.0, 0.0, 0.0]
        p[a_axis] = origin[a_axis] + (idx[a_axis] + u) * voxel_size
        p[b_axis] = origin[b_axis] + (idx[b_axis] + v) * voxel_size
        p[e_axis] = origin[e_axis] + (idx[e_axis] + e) * voxel_size
        return tuple(p)

    # The cut removes exactly the corner at (u_cut, v_cut); `far` is the
    # opposite corner and `hyp_a`/`hyp_b` are its two neighbours -- together
    # they form the right-triangle cross-section kept after the 45° cut.
    u_cut = 1 if sa > 0 else 0
    v_cut = 1 if sb > 0 else 0
    cut = (u_cut, v_cut)
    far = (1 - u_cut, 1 - v_cut)
    hyp_a = (u_cut, 1 - v_cut)
    hyp_b = (1 - u_cut, v_cut)

    if cap_min:
        bm.faces.new([bm.verts.new(make_point(u, v, 0)) for u, v in (far, hyp_a, hyp_b)])
    elif stitch_min:
        # The e-neighbour here is solid but isn't an identically-oriented
        # ramp (e.g. a plain cube corner), so its cross-section is a full
        # square while this cell's is only the kept triangle. Fill the
        # remaining corner triangle so the two sides meet without a gap.
        bm.faces.new([bm.verts.new(make_point(u, v, 0)) for u, v in (hyp_a, cut, hyp_b)])

    if cap_max:
        bm.faces.new([bm.verts.new(make_point(u, v, 1)) for u, v in (far, hyp_a, hyp_b)])
    elif stitch_max:
        bm.faces.new([bm.verts.new(make_point(u, v, 1)) for u, v in (hyp_a, cut, hyp_b)])

    diag = [bm.verts.new(make_point(u, v, e)) for u, v, e in
            ((hyp_a[0], hyp_a[1], 0), (hyp_b[0], hyp_b[1], 0), (hyp_b[0], hyp_b[1], 1), (hyp_a[0], hyp_a[1], 1))]
    bm.faces.new(diag)


def build_voxel_bmesh(mesh, voxel_size, diagonal_fill=False, padding=2):
    """Voxelize `mesh` (local space) into a watertight low-poly bmesh.

    Returns None if the source has no triangles or ends up empty.
    """
    verts_local, tris = _mesh_local_triangles(mesh)
    if len(tris) == 0:
        return None

    bbox_min = verts_local.min(axis=0)
    bbox_max = verts_local.max(axis=0)

    voxel_size = _clamped_voxel_size(bbox_min, bbox_max, voxel_size, padding)
    dims, origin = _grid_dims_and_origin(bbox_min, bbox_max, voxel_size, padding)

    surface = _voxelize_surface(verts_local, tris, origin, voxel_size, dims)
    filled = ~_flood_fill_outside(surface)
    if not filled.any():
        return None

    avail, ramp_info = _compute_face_availability(filled, diagonal_fill)

    bm = bmesh.new()

    for d_idx, (axis, sign) in enumerate(DIRECTIONS):
        _add_cell_quads(bm, filled, avail[..., d_idx], origin, voxel_size, axis, sign)

    for cell, orientation in ramp_info.items():
        a_axis, b_axis, e_axis, sa, sb = orientation
        idx_neg = list(cell); idx_neg[e_axis] -= 1
        idx_pos = list(cell); idx_pos[e_axis] += 1

        neg_filled = _in_bounds(idx_neg, dims) and filled[tuple(idx_neg)]
        pos_filled = _in_bounds(idx_pos, dims) and filled[tuple(idx_pos)]

        cap_min = not neg_filled
        cap_max = not pos_filled
        stitch_min = neg_filled and ramp_info.get(tuple(idx_neg)) != orientation
        stitch_max = pos_filled and ramp_info.get(tuple(idx_pos)) != orientation

        _emit_ramp_cell(bm, origin, voxel_size, cell, a_axis, b_axis, e_axis, sa, sb,
                        cap_min, cap_max, stitch_min, stitch_max)

    if len(bm.faces) == 0:
        bm.free()
        return None

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=voxel_size * 1e-4)
    # Every quad above is emitted one-per-cell so edges always match exactly;
    # this merges the coplanar interior edges of adjacent flat cells back
    # into bigger n-gons (the actual poly-count reduction) without the
    # T-junction risk a hand-rolled rectangle merge would have.
    bmesh.ops.dissolve_limit(bm, angle_limit=0.001, verts=bm.verts, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    return bm
