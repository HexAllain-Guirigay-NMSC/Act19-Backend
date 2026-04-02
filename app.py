import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from db import mysql

# ================= IMPORT ROUTES =================
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.locations import locations_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ================= MYSQL CONFIG =================
    app.config["MYSQL_HOST"] = Config.DB_HOST
    app.config["MYSQL_USER"] = Config.DB_USER
    app.config["MYSQL_PASSWORD"] = Config.DB_PASSWORD
    app.config["MYSQL_DB"] = Config.DB_NAME
    app.config["MYSQL_CURSORCLASS"] = "DictCursor"

    # ================= OPTIONAL: MAX UPLOAD SIZE =================
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    # ================= CORS =================
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=False
    )

    # ================= INIT MYSQL =================
    mysql.init_app(app)

    # ================= CREATE UPLOAD FOLDERS =================
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.PROFILE_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.LOCATION_UPLOAD_FOLDER, exist_ok=True)

    # ================= REGISTER ALL ROUTES =================
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(locations_bp)

    # ================= TEST ROUTES =================
    @app.route("/", methods=["GET"])
    def home():
        return "GIS Flask Backend API is running..."

    @app.route("/api/test-db", methods=["GET"])
    def test_db():
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT 1 AS test")
            result = cur.fetchone()
            cur.close()

            return jsonify({
                "success": True,
                "result": result
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Database connection failed.",
                "error": str(e)
            }), 500

    # ================= SERVE UPLOADED FILES =================
    @app.route("/uploads/<path:filename>", methods=["GET"])
    def uploaded_file(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    return app


# ================= RUN APP =================
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=Config.PORT)