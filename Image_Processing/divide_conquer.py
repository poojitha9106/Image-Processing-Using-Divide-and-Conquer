def divide_image(image, depth, x=0, y=0):
    """
    Recursively divide an image into four regions.

    Each final region stores:
    1. Cropped image
    2. Original X coordinate
    3. Original Y coordinate
    """

    width, height = image.size


    # =====================================================
    # BASE CASE
    # =====================================================

    if depth <= 0:

        return [
            (
                image,
                x,
                y
            )
        ]


    # Safety check
    if width < 2 or height < 2:

        return [
            (
                image,
                x,
                y
            )
        ]


    # =====================================================
    # FIND MIDDLE POINT
    # =====================================================

    mid_x = width // 2
    mid_y = height // 2


    # =====================================================
    # DIVIDE INTO FOUR REGIONS
    # =====================================================

    top_left = image.crop(
        (
            0,
            0,
            mid_x,
            mid_y
        )
    )


    top_right = image.crop(
        (
            mid_x,
            0,
            width,
            mid_y
        )
    )


    bottom_left = image.crop(
        (
            0,
            mid_y,
            mid_x,
            height
        )
    )


    bottom_right = image.crop(
        (
            mid_x,
            mid_y,
            width,
            height
        )
    )


    # =====================================================
    # RECURSIVE DIVISION
    # =====================================================

    regions = []


    # Top Left
    regions.extend(

        divide_image(
            top_left,
            depth - 1,
            x,
            y
        )

    )


    # Top Right
    regions.extend(

        divide_image(
            top_right,
            depth - 1,
            x + mid_x,
            y
        )

    )


    # Bottom Left
    regions.extend(

        divide_image(
            bottom_left,
            depth - 1,
            x,
            y + mid_y
        )

    )


    # Bottom Right
    regions.extend(

        divide_image(
            bottom_right,
            depth - 1,
            x + mid_x,
            y + mid_y
        )

    )


    return regions