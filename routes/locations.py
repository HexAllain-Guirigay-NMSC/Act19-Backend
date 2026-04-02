from flask import Blueprint, request, jsonify, g

from db import mysql
from config import Config
from utils.auth_middleware import token_required
from utils.file_helper import save_uploaded_file, delete_local_file
from utils.map_helper import download_static_map_image


locations_bp = Blueprint("locations_bp", __name__)


# ================= CREATE =================
@locations_bp.route("/api/locations", methods=["POST"])
@token_required
def create_location():
    cur = None
    image_path = None

    try:
        location = request.form.get("location", "").strip()
        description = request.form.get("description")
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        city = request.form.get("city")
        province = request.form.get("province")
        source_type = request.form.get("source_type", "").strip()
        image_file = request.files.get("image")

        if not location or not latitude or not longitude:
            return jsonify({
                "success": False,
                "message": "Location, latitude, and longitude are required."
            }), 400

        if image_file and image_file.filename:
            try:
                image_path = save_uploaded_file(
                    image_file,
                    Config.LOCATION_UPLOAD_FOLDER,
                    "locations"
                )
            except ValueError as ve:
                return jsonify({
                    "success": False,
                    "message": str(ve)
                }), 400
        else:
            image_path = download_static_map_image(latitude, longitude)

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO locations (
                user_id, location, description,
                latitude, longitude, city, province,
                image_path, source_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            g.current_user["user_id"],
            location,
            description if description != "" else None,
            latitude,
            longitude,
            city if city != "" else None,
            province if province != "" else None,
            image_path,
            source_type if source_type else ("manual" if image_file else "generated")
        ))
        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Location added successfully."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        if image_path:
            delete_local_file(image_path, Config.BASE_DIR)

        return jsonify({
            "success": False,
            "message": "Failed to add location.",
            "error": str(e)
        }), 500


# ================= GET ALL (PROTECTED + USER ONLY) =================
@locations_bp.route("/api/locations", methods=["GET"])
@token_required
def get_locations():
    cur = None

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT
                l.*,
                u.username,
                u.fullname
            FROM locations l
            JOIN users u ON l.user_id = u.user_id
            WHERE l.user_id = %s
            ORDER BY l.location_id DESC
        """, (g.current_user["user_id"],))
        result = cur.fetchall()
        cur.close()

        return jsonify(result), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Failed to fetch locations.",
            "error": str(e)
        }), 500


# ================= GET ONE (PROTECTED + OWNER ONLY) =================
@locations_bp.route("/api/locations/<int:location_id>", methods=["GET"])
@token_required
def get_one_location(location_id):
    cur = None

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT
                l.*,
                u.username,
                u.fullname
            FROM locations l
            JOIN users u ON l.user_id = u.user_id
            WHERE l.location_id = %s
            LIMIT 1
        """, (location_id,))
        result = cur.fetchone()
        cur.close()

        if not result:
            return jsonify({
                "success": False,
                "message": "Location not found."
            }), 404

        # 🔒 OWNER CHECK
        if int(result["user_id"]) != int(g.current_user["user_id"]):
            return jsonify({
                "success": False,
                "message": "You are not allowed to view this location."
            }), 403

        return jsonify(result), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Failed to fetch location.",
            "error": str(e)
        }), 500


# ================= UPDATE =================
@locations_bp.route("/api/locations/<int:location_id>", methods=["PUT"])
@token_required
def update_location(location_id):
    cur = None
    new_image_path = None

    try:
        location = request.form.get("location")
        description = request.form.get("description")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        city = request.form.get("city")
        province = request.form.get("province")
        source_type = request.form.get("source_type")
        image_file = request.files.get("image")

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT *
            FROM locations
            WHERE location_id = %s
            LIMIT 1
        """, (location_id,))
        existing = cur.fetchone()

        if not existing:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Location not found."
            }), 404

        if int(existing["user_id"]) != int(g.current_user["user_id"]):
            cur.close()
            return jsonify({
                "success": False,
                "message": "You are not allowed to update this location."
            }), 403

        final_location = location.strip() if location and location.strip() else existing["location"]
        final_description = description if description is not None else existing["description"]
        final_latitude = latitude.strip() if latitude and latitude.strip() else str(existing["latitude"])
        final_longitude = longitude.strip() if longitude and longitude.strip() else str(existing["longitude"])
        final_city = city if city is not None else existing["city"]
        final_province = province if province is not None else existing["province"]
        final_source_type = source_type if source_type else existing["source_type"]

        old_image_path = existing["image_path"]
        final_image_path = old_image_path

        if image_file and image_file.filename:
            new_image_path = save_uploaded_file(
                image_file,
                Config.LOCATION_UPLOAD_FOLDER,
                "locations"
            )
            final_image_path = new_image_path
            final_source_type = "manual"

        cur.execute("""
            UPDATE locations
            SET location=%s, description=%s, latitude=%s, longitude=%s,
                city=%s, province=%s, image_path=%s, source_type=%s
            WHERE location_id=%s
        """, (
            final_location,
            final_description,
            final_latitude,
            final_longitude,
            final_city,
            final_province,
            final_image_path,
            final_source_type,
            location_id
        ))
        mysql.connection.commit()
        cur.close()

        if image_file and old_image_path and old_image_path != final_image_path:
            delete_local_file(old_image_path, Config.BASE_DIR)

        return jsonify({
            "success": True,
            "message": "Location updated successfully."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        if new_image_path:
            delete_local_file(new_image_path, Config.BASE_DIR)

        return jsonify({
            "success": False,
            "message": "Failed to update location.",
            "error": str(e)
        }), 500


# ================= DELETE =================
@locations_bp.route("/api/locations/<int:location_id>", methods=["DELETE"])
@token_required
def delete_location(location_id):
    cur = None

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT *
            FROM locations
            WHERE location_id = %s
            LIMIT 1
        """, (location_id,))
        existing = cur.fetchone()

        if not existing:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Location not found."
            }), 404

        if int(existing["user_id"]) != int(g.current_user["user_id"]):
            cur.close()
            return jsonify({
                "success": False,
                "message": "You are not allowed to delete this location."
            }), 403

        old_image_path = existing["image_path"]

        cur.execute("DELETE FROM locations WHERE location_id = %s", (location_id,))
        mysql.connection.commit()
        cur.close()

        if old_image_path:
            delete_local_file(old_image_path, Config.BASE_DIR)

        return jsonify({
            "success": True,
            "message": "Location deleted successfully."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Failed to delete location.",
            "error": str(e)
        }), 500