from PIL import Image, ImageFilter, ImageEnhance, ImageOps


def process_region(region, operation="grayscale"):
    """
    Process an individual image region based on the requested operation.
    """

    if region is None:
        raise ValueError("Invalid image region.")

    # Ensure region is RGB before color transforms
    if region.mode != "RGB":
        region = region.convert("RGB")

    operation = (operation or "grayscale").lower()

    if operation == "grayscale":
        return region.convert("L")

    elif operation == "edge_detection":
        # Convert to grayscale first for crisp edge highlight
        gray = region.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        return edges.filter(ImageFilter.EDGE_ENHANCE_MORE)

    elif operation == "sepia":
        # Apply sepia tone transformation matrix
        width, height = region.size
        pixels = region.load()

        sepia_img = Image.new("RGB", (width, height))
        sepia_pixels = sepia_img.load()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)

                sepia_pixels[x, y] = (
                    min(255, tr),
                    min(255, tg),
                    min(255, tb)
                )

        return sepia_img

    elif operation == "blur":
        return region.filter(ImageFilter.GaussianBlur(radius=3))

    elif operation == "contrast":
        enhancer = ImageEnhance.Contrast(region)
        return enhancer.enhance(1.8)

    elif operation == "invert":
        return ImageOps.invert(region)

    elif operation == "sharpen":
        return region.filter(ImageFilter.SHARPEN)

    else:
        # Default fallback to grayscale
        return region.convert("L")


def combine_regions(regions, original_size):
    """
    Combine processed regions at their original x and y coordinates.
    Automatically detects color mode (RGB or L) from processed regions.
    """

    width, height = original_size

    if width <= 0 or height <= 0:
        raise ValueError("Invalid original image size.")

    if not regions:
        raise ValueError("No regions provided to combine.")

    # Determine canvas mode from first region
    sample_region = regions[0][0]
    canvas_mode = sample_region.mode if sample_region else "RGB"
    default_color = 255 if canvas_mode == "L" else (255, 255, 255)

    combined_image = Image.new(
        canvas_mode,
        (width, height),
        color=default_color
    )

    for region, x, y in regions:
        if region is None:
            continue

        if region.mode != canvas_mode:
            region = region.convert(canvas_mode)

        combined_image.paste(
            region,
            (int(x), int(y))
        )

    return combined_image