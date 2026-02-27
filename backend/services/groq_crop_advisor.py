"""
Groq Crop Advisor — Suggests region-appropriate crops using Groq LLM.

When a farmer selects their state/district during onboarding, this service
suggests 8-12 crops suitable for their region and current season.

Falls back to a curated static map if Groq is unavailable or times out.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger('groq_crop_advisor')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_TIMEOUT_SECONDS = 3


# ─── Static fallback: curated crops per state ───────────────────
CROP_DB = {
    'Karnataka': [
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Coconut', 'icon': '🥥', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Ragi', 'icon': '🌾', 'perishable': False},
        {'name': 'Jowar', 'icon': '🌾', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Arecanut', 'icon': '🌴', 'perishable': False},
        {'name': 'Sunflower', 'icon': '🌻', 'perishable': False},
    ],
    'Maharashtra': [
        {'name': 'Soybean', 'icon': '🫘', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Jowar', 'icon': '🌾', 'perishable': False},
        {'name': 'Bajra', 'icon': '🌾', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
        {'name': 'Grapes', 'icon': '🍇', 'perishable': True},
        {'name': 'Pomegranate', 'icon': '🍎', 'perishable': True},
    ],
    'Madhya Pradesh': [
        {'name': 'Soybean', 'icon': '🫘', 'perishable': False},
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Lentils', 'icon': '🫘', 'perishable': False},
        {'name': 'Gram', 'icon': '🫘', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
    ],
    'Punjab': [
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Bajra', 'icon': '🌾', 'perishable': False},
    ],
    'Uttar Pradesh': [
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Gram', 'icon': '🫘', 'perishable': False},
        {'name': 'Lentils', 'icon': '🫘', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    ],
    'Tamil Nadu': [
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Coconut', 'icon': '🥥', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Banana', 'icon': '🍌', 'perishable': True},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Turmeric', 'icon': '🌿', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
    ],
    'Andhra Pradesh': [
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Chilli', 'icon': '🌶️', 'perishable': True},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Coconut', 'icon': '🥥', 'perishable': False},
        {'name': 'Mango', 'icon': '🥭', 'perishable': True},
    ],
    'Telangana': [
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Soybean', 'icon': '🫘', 'perishable': False},
        {'name': 'Chilli', 'icon': '🌶️', 'perishable': True},
        {'name': 'Turmeric', 'icon': '🌿', 'perishable': False},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    ],
    'Rajasthan': [
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Bajra', 'icon': '🌾', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Gram', 'icon': '🫘', 'perishable': False},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Cumin', 'icon': '🌿', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
    ],
    'Gujarat': [
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Bajra', 'icon': '🌾', 'perishable': False},
        {'name': 'Cumin', 'icon': '🌿', 'perishable': False},
        {'name': 'Castor', 'icon': '🌿', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    ],
    'Kerala': [
        {'name': 'Coconut', 'icon': '🥥', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Banana', 'icon': '🍌', 'perishable': True},
        {'name': 'Rubber', 'icon': '🌿', 'perishable': False},
        {'name': 'Pepper', 'icon': '🌶️', 'perishable': False},
        {'name': 'Cardamom', 'icon': '🌿', 'perishable': False},
        {'name': 'Arecanut', 'icon': '🌴', 'perishable': False},
        {'name': 'Tapioca', 'icon': '🌿', 'perishable': True},
    ],
    'West Bengal': [
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Jute', 'icon': '🌿', 'perishable': False},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    ],
    'Bihar': [
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Maize', 'icon': '🌽', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Lentils', 'icon': '🫘', 'perishable': False},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
        {'name': 'Onion', 'icon': '🧅', 'perishable': True},
        {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    ],
    'Haryana': [
        {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
        {'name': 'Rice', 'icon': '🌾', 'perishable': False},
        {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
        {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
        {'name': 'Mustard', 'icon': '🌻', 'perishable': False},
        {'name': 'Bajra', 'icon': '🌾', 'perishable': False},
        {'name': 'Potato', 'icon': '🥔', 'perishable': False},
    ],
}

# Default fallback for unlisted states
DEFAULT_CROPS = [
    {'name': 'Rice', 'icon': '🌾', 'perishable': False},
    {'name': 'Wheat', 'icon': '🌿', 'perishable': False},
    {'name': 'Maize', 'icon': '🌽', 'perishable': False},
    {'name': 'Soybean', 'icon': '🫘', 'perishable': False},
    {'name': 'Cotton', 'icon': '☁️', 'perishable': False},
    {'name': 'Sugarcane', 'icon': '🎋', 'perishable': False},
    {'name': 'Groundnut', 'icon': '🥜', 'perishable': False},
    {'name': 'Onion', 'icon': '🧅', 'perishable': True},
    {'name': 'Tomato', 'icon': '🍅', 'perishable': True},
    {'name': 'Potato', 'icon': '🥔', 'perishable': False},
]

# Icon lookup for LLM-suggested crops
EMOJI_MAP = {
    'rice': '🌾', 'wheat': '🌿', 'maize': '🌽', 'corn': '🌽',
    'soybean': '🫘', 'soya': '🫘', 'cotton': '☁️', 'sugarcane': '🎋',
    'groundnut': '🥜', 'peanut': '🥜', 'onion': '🧅', 'tomato': '🍅',
    'potato': '🥔', 'coconut': '🥥', 'banana': '🍌', 'mango': '🥭',
    'grapes': '🍇', 'grape': '🍇', 'chilli': '🌶️', 'pepper': '🌶️',
    'sunflower': '🌻', 'mustard': '🌻', 'ragi': '🌾', 'jowar': '🌾',
    'bajra': '🌾', 'arecanut': '🌴', 'pomegranate': '🍎', 'turmeric': '🌿',
    'cumin': '🌿', 'cardamom': '🌿', 'rubber': '🌿', 'jute': '🌿',
    'gram': '🫘', 'lentils': '🫘', 'castor': '🌿', 'tapioca': '🌿',
}

PERISHABLE_CROPS = {
    'tomato', 'onion', 'banana', 'grapes', 'grape', 'mango',
    'chilli', 'pepper', 'tapioca', 'pomegranate',
}


def get_current_season():
    """Return the Indian agricultural season based on current month."""
    month = datetime.now().month
    if month in (6, 7, 8, 9, 10):
        return 'Kharif (monsoon)'
    elif month in (11, 12, 1, 2, 3):
        return 'Rabi (winter)'
    else:
        return 'Zaid (summer)'


def suggest_crops(state, district=None):
    """
    Suggest crops for a given state + district.
    Uses Groq if available, falls back to curated static list.
    """
    # Try Groq first (if API key is set)
    if GROQ_API_KEY:
        try:
            return _groq_suggest(state, district)
        except Exception as e:
            logger.warning(f"Groq crop suggestion failed: {e} — using static fallback")

    # Static fallback
    return _static_suggest(state)


def _static_suggest(state):
    """Return crops from the curated per-state database."""
    state_key = state.strip() if state else ''

    # Try exact match first
    if state_key in CROP_DB:
        return {'crops': CROP_DB[state_key], 'source': 'curated'}

    # Try case-insensitive match
    for key, crops in CROP_DB.items():
        if key.lower() == state_key.lower():
            return {'crops': crops, 'source': 'curated'}

    return {'crops': DEFAULT_CROPS, 'source': 'default'}


def _groq_suggest(state, district=None):
    """
    Ask Groq to suggest crops for a specific Indian state+district.
    Returns structured JSON crop list.
    """
    import httpx
    from groq import Groq

    season = get_current_season()
    location = f"{district}, {state}" if district else state

    system_prompt = (
        "You are an Indian agricultural expert. "
        "STRICT RULES:\n"
        "1. Return ONLY a JSON array of crop objects.\n"
        "2. Each object: {\"name\": \"CropName\", \"perishable\": true/false}\n"
        "3. Suggest 8-12 crops that are actually grown in the specified region.\n"
        "4. Include a mix of food grains, cash crops, and vegetables.\n"
        "5. Order by popularity/importance in that region.\n"
        "6. Do NOT include any explanation, just the JSON array."
    )

    user_prompt = (
        f"Suggest crops for a farmer in {location}, India.\n"
        f"Current season: {season}.\n"
        f"Return ONLY a JSON array like: "
        f'[{{"name": "Rice", "perishable": false}}, {{"name": "Tomato", "perishable": true}}]'
    )

    client = Groq(
        api_key=GROQ_API_KEY,
        timeout=httpx.Timeout(GROQ_TIMEOUT_SECONDS, connect=1.0),
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=500,
        top_p=0.9,
    )

    raw = response.choices[0].message.content.strip()

    # Clean up: extract JSON array from response
    if raw.startswith('```'):
        # Strip markdown code fences
        raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

    crops_raw = json.loads(raw)

    # Normalize and add icons
    crops = []
    for c in crops_raw:
        name = c.get('name', '').strip()
        if not name:
            continue
        perishable = c.get('perishable', name.lower() in PERISHABLE_CROPS)
        icon = EMOJI_MAP.get(name.lower(), '🌱')
        crops.append({
            'name': name,
            'icon': icon,
            'perishable': perishable,
        })

    if len(crops) < 4:
        # Too few crops from LLM — supplement with static
        return _static_suggest(state)

    return {'crops': crops, 'source': 'groq'}
