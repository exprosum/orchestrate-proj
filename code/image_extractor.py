import os
import json
import re
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CACHE_PATH = Path(__file__).parent / "image_cache.json"

def get_image_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read image cache: {e}")
    return {}

def save_image_cache(cache: dict) -> None:
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save image cache: {e}")

def extract_amount_from_image(image_id: str, image_path: Path, event_id: str = "", user_id: str = "") -> float:
    """
    Extract the monetary amount from an image using Gemini Vision, falling back to cache.
    """
    cache = get_image_cache()
    if image_id in cache and "amount" in cache[image_id]:
        return float(cache[image_id]["amount"])

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(f"Notice: GEMINI_API_KEY not set. Using cached amount for {image_id}.")
        if image_id in cache:
            return float(cache[image_id]["amount"])
        raise ValueError(f"No API key and no cached amount for image {image_id}")

    # Call Gemini Vision if API key is provided
    try:
        # pyrefly: ignore [missing-import]
        from google import genai
        # pyrefly: ignore [missing-import]
        from google.genai import types
        # pyrefly: ignore [missing-import]
        from PIL import Image

        client = genai.Client(api_key=api_key)
        pil_img = Image.open(image_path)

        prompt = (
            f"Extract the final total monetary amount payable or received from this financial document / receipt / invoice. "
            f"This is for event {event_id} of user {user_id}. "
            f"Return ONLY a single numeric value without currency symbols, commas, or extra text. "
            f"Example format: 1250.50"
        )

        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=[pil_img, prompt]
        )
        text = response.text.strip()
        # Parse numeric value
        match = re.search(r"[-+]?\d*\.?\d+", text.replace(",", ""))
        if match:
            amount = float(match.group())
            cache[image_id] = {
                "event_id": event_id,
                "user_id": user_id,
                "amount": amount,
                "extracted_via": "gemini"
            }
            save_image_cache(cache)
            return amount
        else:
            raise ValueError(f"Could not parse numeric amount from model response: {text}")

    except Exception as e:
        print(f"Gemini API call failed for {image_id}: {e}")
        if image_id in cache:
            return float(cache[image_id]["amount"])
        raise

def get_event_amount_from_image(event_id: str, images_df, media_dir: Path) -> float:
    """
    Helper to look up image for an event_id and return its extracted amount.
    """
    cache = get_image_cache()
    # Check cache directly by event_id
    for img_id, data in cache.items():
        if data.get("event_id") == event_id:
            return float(data["amount"])

    # Look up in images_df
    matches = images_df[images_df["related_event_id"] == event_id]
    if matches.empty:
        raise ValueError(f"No image found for event {event_id}")

    row = matches.iloc[0]
    img_id = row["image_id"]
    img_file = media_dir / f"{img_id}.png"
    return extract_amount_from_image(img_id, img_file, event_id=event_id, user_id=row.get("user_id", ""))
