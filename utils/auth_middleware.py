import jwt
from functools import wraps
from flask import request, jsonify, g

from config import Config
from db import mysql


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            auth_header = request.headers.get("Authorization", "")

            if not auth_header.startswith("Bearer "):
                return jsonify({
                    "success": False,
                    "message": "Access denied. No token provided."
                }), 401

            token = auth_header.split(" ")[1].strip()

            if not token:
                return jsonify({
                    "success": False,
                    "message": "Access denied. No token provided."
                }), 401

            decoded = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])

            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT user_id, username, email, fullname, profile_image, is_verified, token
                FROM users
                WHERE user_id = %s AND token = %s
                LIMIT 1
            """, (decoded["user_id"], token))
            user = cur.fetchone()
            cur.close()

            if not user:
                return jsonify({
                    "success": False,
                    "message": "Invalid or expired token."
                }), 401

            g.current_user = user
            g.current_token = token

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token."
            }), 401
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Authorization failed.",
                "error": str(e)
            }), 500

    return decorated