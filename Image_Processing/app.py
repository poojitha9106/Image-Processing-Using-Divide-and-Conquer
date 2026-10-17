from flask import Flask, render_template, request, url_for
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
import os
import time
import uuid

from divide_conquer import divide_image
from image_processor import process_region, combine_regions


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# FOLDERS (Absolute Paths using app.root_path)
# =========================================================

BASE_DIR = app.root_path
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DIVIDED_FOLDER = os.path.join(BASE_DIR, "static", "divided")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "outputs")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DIVIDED_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================================================
# SETTINGS
# =========================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

ALLOWED_OPERATIONS = {
    "grayscale": "Grayscale Conversion",
    "edge_detection": "Edge Detection Filter",
    "sepia": "Sepia Tone Filter",
    "blur": "Gaussian Blur Filter",
    "contrast": "Contrast Enhancement",
    "invert": "Color Channel Inversion",
    "sharpen": "Image Sharpening"
}

# Maximum image size = 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# =========================================================
# CHECK FILE EXTENSION
# =========================================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():
    return render_template("index.html", operations=ALLOWED_OPERATIONS)


# =========================================================
# PROCESS IMAGE
# =========================================================

@app.route("/process", methods=["POST"])
def process_image():

    # -----------------------------------------------------
    # CHECK IMAGE
    # -----------------------------------------------------

    if "image" not in request.files:
        return "No image uploaded.", 400

    file = request.files["image"]

    if file.filename == "":
        return "No image selected.", 400

    if not allowed_file(file.filename):
        return (
            "Invalid image format. "
            "Please upload JPG, JPEG, PNG or WEBP.",
            400
        )

    # -----------------------------------------------------
    # GET DEPTH AND OPERATION
    # -----------------------------------------------------

    try:
        depth = int(request.form.get("depth", 2))
    except (ValueError, TypeError):
        depth = 2

    if depth not in [1, 2, 3]:
        depth = 2

    operation = request.form.get("operation", "grayscale").lower()
    if operation not in ALLOWED_OPERATIONS:
        operation = "grayscale"

    operation_name = ALLOWED_OPERATIONS[operation]

    # -----------------------------------------------------
    # SAFE UNIQUE FILE NAME
    # -----------------------------------------------------

    original_filename = secure_filename(file.filename)
    if not original_filename:
        original_filename = "image.jpg"

    base_name, extension = os.path.splitext(original_filename)
    extension = extension.lower()

    # Unique ID prevents browser caching old images
    unique_id = uuid.uuid4().hex[:10]
    saved_filename = f"{base_name}_{unique_id}{extension}"
    input_path = os.path.join(UPLOAD_FOLDER, saved_filename)

    # -----------------------------------------------------
    # SAVE UPLOADED IMAGE
    # -----------------------------------------------------

    try:
        file.save(input_path)
    except Exception as error:
        return f"Error saving uploaded image: {error}", 500

    # -----------------------------------------------------
    # OPEN AND NORMALIZE IMAGE
    # -----------------------------------------------------

    try:
        with Image.open(input_path) as uploaded_image:
            # Fix phone image orientation
            corrected_image = ImageOps.exif_transpose(uploaded_image)

            # Handle transparent images
            if corrected_image.mode in ("RGBA", "LA"):
                rgba_image = corrected_image.convert("RGBA")
                background = Image.new("RGB", rgba_image.size, (255, 255, 255))
                background.paste(rgba_image, (0, 0), rgba_image.getchannel("A"))
                image = background
            elif (
                corrected_image.mode == "P"
                and "transparency" in corrected_image.info
            ):
                rgba_image = corrected_image.convert("RGBA")
                background = Image.new("RGB", rgba_image.size, (255, 255, 255))
                background.paste(rgba_image, (0, 0), rgba_image.getchannel("A"))
                image = background
            else:
                image = corrected_image.convert("RGB")

            image = image.copy()

    except Exception as error:
        return f"Unable to open the image. Error: {error}", 400

    # -----------------------------------------------------
    # IMAGE INFORMATION
    # -----------------------------------------------------

    width, height = image.size
    if width <= 0 or height <= 0:
        return "Invalid image dimensions.", 400

    image_size = f"{width} × {height}"

    # -----------------------------------------------------
    # CHECK MINIMUM SIZE
    # -----------------------------------------------------

    minimum_dimension = 2 ** depth
    if width < minimum_dimension or height < minimum_dimension:
        return (
            f"Image is too small for Depth {depth}. "
            f"Minimum size required is {minimum_dimension} × {minimum_dimension} pixels.",
            400
        )

    # =====================================================
    # DIVIDE STAGE
    # =====================================================

    try:
        divide_start = time.perf_counter()
        regions = divide_image(image, depth)
        divide_end = time.perf_counter()
        divide_time = divide_end - divide_start
    except Exception as error:
        return f"Error during Divide stage: {error}", 500

    if not regions:
        return "No image regions were generated.", 500

    # -----------------------------------------------------
    # VERIFY REGION COUNT
    # -----------------------------------------------------

    expected_regions = 4 ** depth
    if len(regions) != expected_regions:
        return (
            f"Expected {expected_regions} regions but generated {len(regions)} regions.",
            500
        )

    # =====================================================
    # SAVE DIVIDED REGIONS
    # =====================================================

    divided_images = []

    for index, (region, x, y) in enumerate(regions, start=1):
        try:
            divided_filename = f"{base_name}_{unique_id}_region_{index}.jpg"
            divided_path = os.path.join(DIVIDED_FOLDER, divided_filename)

            region_for_display = region.convert("RGB")
            region_for_display.save(divided_path, format="JPEG", quality=95)

            divided_url = url_for("static", filename=f"divided/{divided_filename}")
            divided_images.append(divided_url)

        except Exception as error:
            return f"Error saving Region {index}: {error}", 500

    # =====================================================
    # CONQUER STAGE
    # =====================================================

    processed_regions = []

    try:
        conquer_start = time.perf_counter()

        for index, (region, x, y) in enumerate(regions, start=1):
            processed_region = process_region(region, operation)
            processed_regions.append((processed_region, x, y))

        conquer_end = time.perf_counter()
        conquer_time = conquer_end - conquer_start

    except Exception as error:
        return f"Error during Conquer stage: {error}", 500

    # =====================================================
    # COMBINE STAGE
    # =====================================================

    try:
        combine_start = time.perf_counter()

        final_image = combine_regions(processed_regions, image.size)

        combine_end = time.perf_counter()
        combine_time = combine_end - combine_start

    except Exception as error:
        return f"Error during Combine stage: {error}", 500

    # -----------------------------------------------------
    # VERIFY FINAL IMAGE
    # -----------------------------------------------------

    if final_image.size != image.size:
        return "Final image dimensions do not match the original image.", 500

    # =====================================================
    # TOTAL TIME
    # =====================================================

    total_time = divide_time + conquer_time + combine_time

    # Avoid zero division in stats calculation
    safe_total = total_time if total_time > 0 else 0.000001
    divide_pct = min(100, max(5, int((divide_time / safe_total) * 100)))
    conquer_pct = min(100, max(5, int((conquer_time / safe_total) * 100)))
    combine_pct = min(100, max(5, int((combine_time / safe_total) * 100)))

    # =====================================================
    # SAVE FINAL IMAGE
    # =====================================================

    output_filename = f"processed_{base_name}_{unique_id}.jpg"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        if final_image.mode not in ("RGB", "L"):
            final_for_save = final_image.convert("RGB")
        else:
            final_for_save = final_image

        final_for_save.save(output_path, format="JPEG", quality=95)

    except Exception as error:
        return f"Error saving final image: {error}", 500

    # =====================================================
    # RECURSIVE CALL COUNT
    # =====================================================

    recursive_calls = sum(4 ** level for level in range(depth + 1))

    # =====================================================
    # CREATE CORRECT FLASK STATIC URLS
    # =====================================================

    original_image_url = url_for("static", filename=f"uploads/{saved_filename}")
    processed_image_url = url_for("static", filename=f"outputs/{output_filename}")

    # =====================================================
    # TERMINAL OUTPUT
    # =====================================================

    print()
    print("==========================================")
    print("DIVIDE AND CONQUER IMAGE PROCESSING")
    print("==========================================")
    print("Original file  :", saved_filename)
    print("Image size     :", image_size)
    print("Operation      :", operation_name)
    print("Depth          :", depth)
    print("Regions        :", len(regions))
    print("Recursive calls:", recursive_calls)
    print("Divide time    :", f"{divide_time:.6f}s")
    print("Conquer time   :", f"{conquer_time:.6f}s")
    print("Combine time   :", f"{combine_time:.6f}s")
    print("Total time     :", f"{total_time:.6f}s")
    print("==========================================")
    print()

    # =====================================================
    # DISPLAY RESULTS
    # =====================================================

    return render_template(
        "index.html",
        operations=ALLOWED_OPERATIONS,
        selected_operation=operation,
        operation_name=operation_name,
        original_image=original_image_url,
        processed_image=processed_image_url,
        divided_images=divided_images,
        depth=depth,
        region_count=len(regions),
        image_size=image_size,
        divide_time=f"{divide_time:.6f}",
        conquer_time=f"{conquer_time:.6f}",
        combine_time=f"{combine_time:.6f}",
        total_time=f"{total_time:.6f}",
        divide_pct=divide_pct,
        conquer_pct=conquer_pct,
        combine_pct=combine_pct,
        recursive_calls=recursive_calls
    )


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):
    return "Image is too large. Maximum allowed size is 10 MB.", 413


# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)