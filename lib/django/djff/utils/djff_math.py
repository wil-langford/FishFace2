import math


def euclidean_length(vector):
    return math.sqrt(sum([x**2 for x in vector]))


def rotate_point(point, angle):
    """
    Rotates a point about the origin by an angle given in radians.
    """
    rangle = math.radians(-angle) # negated because the Y axis is inverted in image coords

    sin_a = math.sin(rangle)
    cos_a = math.cos(rangle)

    x, y = point

    return (
        int(x * cos_a - y * sin_a),
        int(x * sin_a + y * cos_a),
    )
