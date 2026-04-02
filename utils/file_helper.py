import os
import uuid
from werkzeug.utils import secure_filename


ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_file(file, folder_path, folder_name):
    if not file or not file.filename:
        return None

    if not allowed_image_file(file.filename):
        raise ValueError("Only image files are allowed.")

    os.makedirs(folder_path, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    absolute_path = os.path.join(folder_path, secure_filename(filename))

    file.save(absolute_path)

    return f"uploads/{folder_name}/{filename}"


def delete_local_file(relative_path, base_dir):
    if not relative_path or not isinstance(relative_path, str):
        return

    if not relative_path.startswith("uploads/"):
        return

    absolute_path = os.path.join(base_dir, relative_path)

    if os.path.exists(absolute_path) and os.path.isfile(absolute_path):
        os.remove(absolute_path)