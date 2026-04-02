import os
import uuid
import requests

from config import Config


def build_static_map_url(latitude, longitude):
    key = Config.MAPQUEST_KEY
    return (
        f"https://www.mapquestapi.com/staticmap/v5/map"
        f"?key={key}"
        f"&center={latitude},{longitude}"
        f"&size=700,400@2x"
        f"&zoom=14"
        f"&locations={latitude},{longitude}|marker-red"
    )


def download_static_map_image(latitude, longitude):
    if not Config.MAPQUEST_KEY:
        raise ValueError("MAPQUEST_KEY is missing in backend .env")

    image_url = build_static_map_url(latitude, longitude)
    response = requests.get(image_url, timeout=30)

    if response.status_code != 200:
        raise ValueError(
            f"Failed to download static map image: {response.status_code} {response.reason}"
        )

    os.makedirs(Config.LOCATION_UPLOAD_FOLDER, exist_ok=True)

    filename = f"map-{uuid.uuid4().hex}.png"
    absolute_path = os.path.join(Config.LOCATION_UPLOAD_FOLDER, filename)

    with open(absolute_path, "wb") as f:
        f.write(response.content)

    return f"uploads/locations/{filename}"