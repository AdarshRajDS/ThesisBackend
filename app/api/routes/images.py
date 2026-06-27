from fastapi import APIRouter
from pathlib import Path
import os

router = APIRouter(prefix="/images", tags=["Images"])


@router.get("/all")
def list_images():

    BASE_DATA_DIR = os.getenv("HF_HOME", ".")
    OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "outputs")

    if not os.path.exists(OUTPUT_DIR):
        return {"images": []}

    image_urls = [
        f"outputs/{file.name}"
        for file in Path(OUTPUT_DIR).glob("*")
        if file.suffix.lower() in [".png", ".jpg", ".jpeg"]
    ]

    return {"images": image_urls}
