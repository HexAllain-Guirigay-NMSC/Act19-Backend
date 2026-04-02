from datetime import datetime
import bcrypt
import jwt

from flask import Blueprint, request, jsonify

from db import mysql
from config import Config
from utils.file_helper import save_uploaded_file, delete_local_file
from utils.token_helper import generate_token, get_expiry
from utils.email_helper import send_verification_email, send_reset_email


auth_bp = Blueprint("auth_bp", __name__)


def serialize_user(user_row):
    return {
        "user_id": user_row["user_id"],
        "username": user_row["username"],
        "email": user_row["email"],
        "fullname": user_row["fullname"],
        "profile_image": user_row.get("profile_image"),
        "is_verified": user_row["is_verified"],
    }


@auth_bp.route("/api/register", methods=["POST"])
def register():
    cur = None
    profile_image_path = None

    try:
        fullname = request.form.get("fullname", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        profile_image_file = request.files.get("profile_image")

        if not fullname or not username or not email or not password:
            return jsonify({
                "success": False,
                "message": "All fields are required."
            }), 400

        cur = mysql.connection.cursor()

        check_sql = """
            SELECT user_id
            FROM users
            WHERE username = %s OR email = %s
        """
        cur.execute(check_sql, (username, email))
        existing_user = cur.fetchone()

        if existing_user:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Username or email already exists."
            }), 400

        if profile_image_file and profile_image_file.filename:
            try:
                profile_image_path = save_uploaded_file(
                    profile_image_file,
                    Config.PROFILE_UPLOAD_FOLDER,
                    "profile"
                )
            except ValueError as ve:
                cur.close()
                return jsonify({
                    "success": False,
                    "message": str(ve)
                }), 400

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        insert_user_sql = """
            INSERT INTO users (username, email, password_hash, fullname, profile_image, is_verified)
            VALUES (%s, %s, %s, %s, %s, 0)
        """
        cur.execute(
            insert_user_sql,
            (username, email, password_hash, fullname, profile_image_path)
        )
        mysql.connection.commit()

        user_id = cur.lastrowid

        verify_token = generate_token()
        expires_at = get_expiry(24)

        insert_token_sql = """
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """
        cur.execute(insert_token_sql, (user_id, verify_token, expires_at))
        mysql.connection.commit()
        cur.close()
        cur = None

        try:
            send_verification_email(email, verify_token)
        except Exception as email_error:
            return jsonify({
                "success": False,
                "message": "User created but verification email failed to send.",
                "error": str(email_error)
            }), 500

        return jsonify({
            "success": True,
            "message": "Registration successful. Please check your email to verify your account."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        if profile_image_path:
            delete_local_file(profile_image_path, Config.BASE_DIR)

        return jsonify({
            "success": False,
            "message": "Registration failed.",
            "error": str(e)
        }), 500


@auth_bp.route("/api/verify-email", methods=["GET"])
def verify_email():
    cur = None

    try:
        token = request.args.get("token", "").strip()

        if not token:
            return jsonify({
                "success": False,
                "message": "Verification token is required."
            }), 400

        cur = mysql.connection.cursor()

        sql = """
            SELECT verify_id, user_id, token, expires_at, used_at
            FROM email_verification_tokens
            WHERE token = %s
            LIMIT 1
        """
        cur.execute(sql, (token,))
        token_row = cur.fetchone()

        if not token_row:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid or expired verification token."
            }), 400

        if token_row["used_at"] is not None:
            cur.close()
            return jsonify({
                "success": False,
                "message": "This verification token has already been used."
            }), 400

        expires_at = token_row["expires_at"]
        if expires_at <= datetime.now():
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid or expired verification token."
            }), 400

        update_user_sql = """
            UPDATE users
            SET is_verified = 1
            WHERE user_id = %s
        """
        cur.execute(update_user_sql, (token_row["user_id"],))

        mark_used_sql = """
            UPDATE email_verification_tokens
            SET used_at = %s
            WHERE verify_id = %s
        """
        cur.execute(mark_used_sql, (datetime.now(), token_row["verify_id"]))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Email verified successfully. You can now log in."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Email verification failed.",
            "error": str(e)
        }), 500


@auth_bp.route("/api/login", methods=["POST"])
def login():
    cur = None

    try:
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required."
            }), 400

        cur = mysql.connection.cursor()

        sql = """
            SELECT user_id, username, email, password_hash, fullname, profile_image, is_verified
            FROM users
            WHERE email = %s
            LIMIT 1
        """
        cur.execute(sql, (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        is_match = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )

        if not is_match:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        if int(user["is_verified"]) != 1:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Please verify your email before logging in."
            }), 403

        token = jwt.encode(
            {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"]
            },
            Config.JWT_SECRET,
            algorithm="HS256"
        )

        update_token_sql = """
            UPDATE users
            SET token = %s
            WHERE user_id = %s
        """
        cur.execute(update_token_sql, (token, user["user_id"]))
        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "token": token,
            "user": serialize_user(user)
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Login failed.",
            "error": str(e)
        }), 500


@auth_bp.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    cur = None

    try:
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()

        if not email:
            return jsonify({
                "success": False,
                "message": "Email is required."
            }), 400

        cur = mysql.connection.cursor()

        user_sql = """
            SELECT user_id, email
            FROM users
            WHERE email = %s
            LIMIT 1
        """
        cur.execute(user_sql, (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            return jsonify({
                "success": False,
                "message": "No account found with that email."
            }), 404

        reset_token = generate_token()
        expires_at = get_expiry(1)

        insert_reset_sql = """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """
        cur.execute(insert_reset_sql, (user["user_id"], reset_token, expires_at))
        mysql.connection.commit()
        cur.close()
        cur = None

        try:
            send_reset_email(email, reset_token)
        except Exception as email_error:
            return jsonify({
                "success": False,
                "message": "Reset token created but reset email failed to send.",
                "error": str(email_error)
            }), 500

        return jsonify({
            "success": True,
            "message": "Password reset link sent."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Failed to send reset link.",
            "error": str(e)
        }), 500


@auth_bp.route("/api/reset-password", methods=["POST"])
def reset_password():
    cur = None

    try:
        data = request.get_json(silent=True) or {}
        token = str(data.get("token", "")).strip()
        new_password = str(data.get("new_password", "")).strip()

        if not token or not new_password:
            return jsonify({
                "success": False,
                "message": "Token and new password are required."
            }), 400

        cur = mysql.connection.cursor()

        token_sql = """
            SELECT reset_id, user_id, token, expires_at, used_at
            FROM password_reset_tokens
            WHERE token = %s
            LIMIT 1
        """
        cur.execute(token_sql, (token,))
        token_row = cur.fetchone()

        if not token_row:
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid or expired reset token."
            }), 400

        if token_row["used_at"] is not None:
            cur.close()
            return jsonify({
                "success": False,
                "message": "This reset token has already been used."
            }), 400

        if token_row["expires_at"] <= datetime.now():
            cur.close()
            return jsonify({
                "success": False,
                "message": "Invalid or expired reset token."
            }), 400

        new_password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        update_user_sql = """
            UPDATE users
            SET password_hash = %s, token = NULL
            WHERE user_id = %s
        """
        cur.execute(update_user_sql, (new_password_hash, token_row["user_id"]))

        mark_used_sql = """
            UPDATE password_reset_tokens
            SET used_at = %s
            WHERE reset_id = %s
        """
        cur.execute(mark_used_sql, (datetime.now(), token_row["reset_id"]))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "success": True,
            "message": "Password reset successful."
        }), 200

    except Exception as e:
        if cur:
            cur.close()

        return jsonify({
            "success": False,
            "message": "Reset password failed.",
            "error": str(e)
        }), 500