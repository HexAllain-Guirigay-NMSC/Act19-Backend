from flask import Blueprint, request, jsonify, g

from db import mysql
from config import Config
from utils.auth_middleware import token_required
from utils.file_helper import save_uploaded_file, delete_local_file


profile_bp = Blueprint("profile_bp", __name__)


@profile_bp.route("/api/profile", methods=["GET"])
@token_required
def get_profile():
    try:
        user = g.current_user

        return jsonify({
            "success": True,
            "user_id": user["user_id"],
            "fullname": user["fullname"],
            "username": user["username"],
            "email": user["email"],
            "profile_image": user.get("profile_image"),
            "is_verified": user["is_verified"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to load profile.",
            "error": str(e)
        }), 500


@profile_bp.route("/api/profile", methods=["PUT"])
@token_required
def update_profile():
    cur = None

    try:
        current_user = g.current_user
        user_id = current_user["user_id"]

        fullname = request.form.get("fullname", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        profile_image_file = request.files.get("profile_image")

        if not fullname or not username or not email:
            return jsonify({
                "success": False,
                "message": "Fullname, username, and email are required."
            }), 400

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT user_id
            FROM users
            WHERE (username = %s OR email = %s) AND user_id <> %s
            LIMIT 1
        """, (username, email, user_id))
        existing = cur.fetchone()

        if existing:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Username or email already exists."
            }), 400

        new_profile_image_path = current_user.get("profile_image")

        if profile_image_file and profile_image_file.filename:
            try:
                saved_path = save_uploaded_file(
                    profile_image_file,
                    Config.PROFILE_UPLOAD_FOLDER,
                    "profile"
                )
                new_profile_image_path = saved_path
            except ValueError as ve:
                cur.close()
                return jsonify({
                    "success": False,
                    "message": str(ve)
                }), 400

        cur.execute("""
            UPDATE users
            SET fullname = %s,
                username = %s,
                email = %s,
                profile_image = %s
            WHERE user_id = %s
        """, (fullname, username, email, new_profile_image_path, user_id))
        mysql.connection.commit()

        cur.execute("""
            SELECT user_id, username, email, fullname, profile_image, is_verified
            FROM users
            WHERE user_id = %s
            LIMIT 1
        """, (user_id,))
        updated_user = cur.fetchone()
        cur.close()
        cur = None

        old_profile_image = current_user.get("profile_image")
        if profile_image_file and profile_image_file.filename and old_profile_image and old_profile_image != new_profile_image_path:
            delete_local_file(old_profile_image, Config.BASE_DIR)

        return jsonify({
            "success": True,
            "message": "Profile updated successfully.",
            "user": {
                "user_id": updated_user["user_id"],
                "fullname": updated_user["fullname"],
                "username": updated_user["username"],
                "email": updated_user["email"],
                "profile_image": updated_user.get("profile_image"),
                "is_verified": updated_user["is_verified"]
            }
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Failed to update profile.",
            "error": str(e)
        }), 500


@profile_bp.route("/api/logout", methods=["POST"])
@token_required
def logout():
    cur = None

    try:
        user_id = g.current_user["user_id"]

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users
            SET token = NULL
            WHERE user_id = %s
        """, (user_id,))
        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Logout successful."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Logout failed.",
            "error": str(e)
        }), 500