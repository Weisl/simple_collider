import numpy as np


def distance_to_capsule(params, points):
    # Extract capsule parameters
    h, r = params

    # Initialize sum of distances
    sum_distances = 0

    for point in points:
        # Calculate distance to the capsule
        distance = np.linalg.norm(point - closest_point_on_capsule(point, h, r))

        # Add distance to the sum
        sum_distances += distance

    return sum_distances


def closest_point_on_capsule(point, h, r):
    # Calculate the centerline vector
    centerline = np.array([0, 0, h])

    # Calculate the direction vector of the centerline
    direction = centerline / np.linalg.norm(centerline)

    # Calculate the projection of the point onto the centerline
    projection = np.dot(point, direction) * direction

    # Calculate the point on the centerline closest to the given point
    closest_point_on_centerline = np.clip(projection, 0, h)

    # Calculate the vector from the closest point on the centerline to the given point
    displacement = point - closest_point_on_centerline

    # Calculate the distance from the point to the centerline
    distance_to_centerline = np.linalg.norm(displacement)

    # Calculate the closest point on the capsule surface to the given point
    if distance_to_centerline < r:
        # Point is inside the cylinder, so the closest point is on the centerline
        closest_point = closest_point_on_centerline
    else:
        # Point is outside the cylinder, so the closest point is on the cylinder surface
        direction_normalized = direction / np.linalg.norm(direction)
        closest_point = closest_point_on_centerline + r * displacement / distance_to_centerline

    return closest_point


def calculate_bounding_capsule(points):
    # Initial guess for capsule parameters (height and radius)
    h, r = 1.0, 1.0

    # Set the step size for adjusting parameters
    step_size = 0.1

    # Set the maximum number of iterations
    max_iterations = 100

    # Initialize the minimum distance to a large value
    min_distance = float("inf")

    # Perform optimization to find the optimal capsule parameters
    for _ in range(max_iterations):
        updated = False

        # Check if increasing the height improves the distance
        new_h = h + step_size
        distance = distance_to_capsule((new_h, r), points)
        if distance < min_distance:
            min_distance = distance
            h = new_h
            updated = True

        # Check if decreasing the height improves the distance
        new_h = h - step_size
        distance = distance_to_capsule((new_h, r), points)
        if distance < min_distance:
            min_distance = distance
            h = new_h
            updated = True

        # Check if increasing the radius improves the distance
        new_r = r + step_size
        distance = distance_to_capsule((h, new_r), points)
        if distance < min_distance:
            min_distance = distance
            r = new_r
            updated = True

        # Check if decreasing the radius improves the distance
        new_r = r - step_size
        distance = distance_to_capsule((h, new_r), points)
        if distance < min_distance:
            min_distance = distance
            r = new_r
            updated = True

        # Break the loop if no update was made in the current iteration
        if not updated:
            break

    return h, r
