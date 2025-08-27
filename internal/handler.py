def interpolate(x_0: float, y_0: float, x_1: float, y_1: float, n: int):
    """
    Interpolates a line between two points `(x_0,y_0)` and `(x_1,y_1)` with a list of sub points. 
    The number of sub points to use is specified. The interpolated path, including the specified initial points, is returned. 
    param: x_0 [float] The specified initial x coord
    param: y_0 [float] The specified initial y coord
    param: x_1 [float] The specified final x coord
    param: y_1 [float] The specified final y coord
    return: The interpolated path as a list of x coords and another list of y coords.  
    """

    # put specified points in interpolated list first
    pts_x, pts_y = [x_0, x_1], [y_0, y_1]
    # find mid-points of current list contents iteratively 
    for i in range(0, n):    
        # current mid-points; add first point
        new_pts_x, new_pts_y = [], []
        new_pts_x.append(pts_x[0])
        new_pts_y.append(pts_y[0])

        N = min(len(pts_x), len(pts_y))
        for i in range(0, N - 1):
            # add mid point between initial and final points; add final point 
            # the initial point has already been added
            new_pts_x.append((pts_x[i] + pts_x[i + 1]) / 2)
            new_pts_y.append((pts_y[i] + pts_y[i + 1]) / 2)
            new_pts_x.append(pts_x[i + 1])
            new_pts_y.append(pts_y[i + 1])
        # new pts has the old pts and its mid points in order
        pts_x = new_pts_x # set new pts list and repeat the loop
        pts_y = new_pts_y
    return pts_x, pts_y
 