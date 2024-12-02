import numpy as np


class ProjectorStack:
    """
    Stack of points that are shifted / projected to put the first one at origin.
    """

    def __init__(self, vec):
        """
        Initialize the ProjectorStack with a list of vectors.

        Args:
            vec (list): List of vectors.
        """
        self.vs = np.array(vec)

    def push(self, v):
        """
        Add a new vector to the stack.

        Args:
            v (np.array): Vector to add.

        Returns:
            ProjectorStack: Updated stack.
        """
        if len(self.vs) == 0:
            self.vs = np.array([v])
        else:
            self.vs = np.append(self.vs, [v], axis=0)
        return self

    def pop(self):
        """
        Remove the last vector from the stack.

        Returns:
            np.array: The removed vector.
        """
        if len(self.vs) > 0:
            ret, self.vs = self.vs[-1], self.vs[:-1]
            return ret

    def __mul__(self, v):
        """
        Multiply the stack of vectors by a given vector.

        Args:
            v (np.array): Vector to multiply with.

        Returns:
            np.array: Resulting vector after multiplication.
        """
        s = np.zeros(len(v))
        for vi in self.vs:
            s = s + vi * np.dot(vi, v)
        return s


class GaertnerBoundary:
    """
    GärtnerBoundary

    Manages the boundary conditions based on Gärtner's paper.

    Attributes:
        projector (ProjectorStack): Projector stack for managing points.
        centers (np.array): Array of center points.
        square_radii (np.array): Array of squared radii.
        empty_center (np.array): Empty center array.
    """

    def __init__(self, pts):
        """
        Initialize the GärtnerBoundary with a list of points.

        Args:
            pts (list): List of points.
        """
        self.projector = ProjectorStack([])
        self.centers, self.square_radii = np.array([]), np.array([])
        self.empty_center = np.array([np.NaN for _ in pts[0]])


def push_if_stable(bound, pt):
    """
    Attempts to push a point into the boundary if stable.

    Args:
        bound (GaertnerBoundary): The boundary to push into.
        pt (np.array): The point to push.

    Returns:
        bool: True if the point was successfully pushed, False otherwise.
    """

    if len(bound.centers) == 0:
        bound.square_radii = np.append(bound.square_radii, 0.0)
        bound.centers = np.array([pt])
        return True
    q0, center = bound.centers[0], bound.centers[-1]
    C, r2 = center - q0, bound.square_radii[-1]
    Qm, M = pt - q0, bound.projector
    Qm_bar = M * Qm
    residue, e = Qm - Qm_bar, sqr_dist(Qm, C) - r2
    z, tol = 2 * sqr_norm(residue), np.finfo(float).eps * max(r2, 1.0)
    is_stable = np.abs(z) > tol
    if is_stable:
        center_new = center + (e / z) * residue
        r2new = r2 + (e * e) / (2 * z)
        bound.projector.push(residue / np.linalg.norm(residue))
        bound.centers = np.append(
            bound.centers, np.array([center_new]), axis=0)
        bound.square_radii = np.append(bound.square_radii, r2new)
    return is_stable


def pop(bound):
    """
    Removes the last point from the boundary.

    Args:
        bound (GaertnerBoundary): The boundary to remove the point from.

    Returns:
        GaertnerBoundary: Updated boundary.
    """
    n = len(bound.centers)
    bound.centers = bound.centers[:-1]
    bound.square_radii = bound.square_radii[:-1]
    if n >= 2:
        bound.projector.pop()
    return bound


class NSphere:
    """
    Represents a hypersphere with a center and squared radius.

    Attributes:
        center (np.array): Center of the n-sphere.
        sqr_radius (float): Squared radius of the n-sphere.
    """

    def __init__(self, c, sqr):
        """
        Initialize the NSphere with a center and squared radius.

        Args:
            c (np.array): Center of the n-sphere.
            sqr (float): Squared radius of the n-sphere.
        """
        self.center = np.array(c)
        self.sqr_radius = sqr


def is_inside(pt, nsphere, atol=1e-6, rtol=0.0):
    """
    Checks if a point is inside the n-sphere.

    Args:
        pt (np.array): The point to check.
        nsphere (NSphere): The n-sphere to check against.
        atol (float): Absolute tolerance for closeness check.
        rtol (float): Relative tolerance for closeness check.

    Returns:
        bool: True if the point is inside the n-sphere, False otherwise.
    """
    r2, R2 = sqr_dist(pt, nsphere.center), nsphere.sqr_radius
    return r2 <= R2 or np.isclose(r2, R2, atol=atol ** 2, rtol=rtol ** 2)


def all_inside(pts, nsphere, atol=1e-6, rtol=0.0):
    """
    Checks if all points are inside the n-sphere.

    Args:
        pts (list): List of points to check.
        nsphere (NSphere): The n-sphere to check against.
        atol (float): Absolute tolerance for closeness check.
        rtol (float): Relative tolerance for closeness check.

    Returns:
        bool: True if all points are inside the n-sphere, False otherwise.
    """
    return all(is_inside(p, nsphere, atol, rtol) for p in pts)


def move_to_front(pts, i):
    """
    Moves a point to the front of the list.

    Args:
        pts (list): List of points.
        i (int): Index of the point to move.

    Returns:
        list: Updated list of points.
    """
    pt = pts[i]
    for j in range(len(pts)):
        pts[j], pt = pt, np.array(pts[j])
        if j == i:
            break
    return pts


def dist(p1, p2):
    """
    Calculates the Euclidean distance between two points.

    Args:
        p1 (np.array): First point.
        p2 (np.array): Second point.

    Returns:
        float: Euclidean distance between the points.
    """
    return np.linalg.norm(p1 - p2)


def sqr_dist(p1, p2):
    """
    Calculates the squared distance between two points.

    Args:
        p1 (np.array): First point.
        p2 (np.array): Second point.

    Returns:
        float: Squared distance between the points.
    """
    return sqr_norm(p1 - p2)


def sqr_norm(p):
    """
    Calculates the squared norm of a point.

    Args:
        p (np.array): Point to calculate the squared norm for.

    Returns:
        float: Squared norm of the point.
    """
    return np.sum(np.array([x * x for x in p]))


def is_max_length(bound):
    """
    Checks if the boundary has reached its maximum length.

    Args:
        bound (GaertnerBoundary): The boundary to check.

    Returns:
        bool: True if the boundary is at maximum length, False otherwise.
    """
    len(bound.centers) == len(bound.empty_center) + 1


def makeNSphere(bound):
    """
    Creates an n-sphere from the boundary.

    Args:
        bound (GaertnerBoundary): The boundary to create the n-sphere from.

    Returns:
        NSphere: The created n-sphere.
    """
    if len(bound.centers) == 0:
        return NSphere(bound.empty_center, 0.0)
    return NSphere(bound.centers[-1], bound.square_radii[-1])


def _welzl(pts, pos, bdry):
    """
    Recursive helper function for Welzl's algorithm.

    Args:
        pts (list): List of points.
        pos (int): Current position in the list of points.
        bdry (GaertnerBoundary): Current boundary.

    Returns:
        tuple: The resulting n-sphere and support count.
    """
    support_count, nsphere = 0, makeNSphere(bdry)
    if is_max_length(bdry):
        return nsphere, 0
    for i in range(pos):
        if not is_inside(pts[i], nsphere):
            is_stable = push_if_stable(bdry, pts[i])
            if is_stable:
                nsphere, s = _welzl(pts, i, bdry)
                pop(bdry)
                move_to_front(pts, i)
                support_count = s + 1
    return nsphere, support_count


def find_max_excess(nsphere, pts, k1):
    """
    Finds the point with the maximum excess error.

    Args:
        nsphere (NSphere): The current n-sphere.
        pts (list): List of points.
        k1 (int): Starting index for the search.

    Returns:
        tuple: The maximum error and index of the point with maximum error.
    """
    err_max, k_max = -np.Inf, k1 - 1
    for (k, pt) in enumerate(pts[k_max:]):
        err = sqr_dist(pt, nsphere.center) - nsphere.sqr_radius
        if err > err_max:
            err_max, k_max = err, k + k1
    return err_max, k_max - 1


def welzl(points, max_iterations=2000):
    """
    Finds the smallest enclosing n-sphere for a set of points.

    Args:
        points (list): List of points.
        max_iterations (int): Maximum number of iterations.

    Returns:
        NSphere: The resulting smallest enclosing n-sphere.
    """
    pts, eps = np.array(points, copy=True), np.finfo(float).eps
    bdry, t = GaertnerBoundary(pts), 1
    nsphere, s = _welzl(pts, t, bdry)
    for i in range(max_iterations):
        e, k = find_max_excess(nsphere, pts, t + 1)
        if e <= eps:
            break
        pt = pts[k]
        push_if_stable(bdry, pt)
        nsphere_new, s_new = _welzl(pts, s, bdry)
        pop(bdry)
        move_to_front(pts, k)
        nsphere = nsphere_new
        t, s = s + 1, s_new + 1
    return nsphere
