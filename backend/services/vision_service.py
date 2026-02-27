import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class VisionService:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    @staticmethod
    def analyze_leaf_image(image_b64, crop_name="Crop"):
        """
        Uses Llama 3.2 Vision to identify pests/diseases from a leaf image.
        Returns a JSON-like dict with findings and market risk impact.
        """
        if not os.getenv("GROQ_API_KEY"):
            return {
                "identified": "Unavailable",
                "confidence": 0,
                "advice": "AI Service not configured.",
                "market_risk": "LOW"
            }

        prompt = f"""
        Analyze this image of a {crop_name} leaf. 
        Identify any pests, diseases, or nutrient deficiencies.
        
        Respond ONLY in the following JSON format:
        {{
            "condition": "Name of disease/pest identified",
            "confidence": "low/medium/high",
            "findings": "Brief 1-sentence description of what you see",
            "treatment": "Top 2 immediate actions for the farmer",
            "market_risk_impact": "LOW/MEDIUM/HIGH (How much this outbreak affects local market price if it spreads)",
            "severity_color": "green/orange/red"
        }}
        """

        try:
            completion = VisionService.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={ "type": "json_object" }
            )

            import json
            return json.loads(completion.choices[0].message.content)

        except Exception as e:
            print(f"Vision API Error: {e}")
            return {
                "condition": "Analysis Failed",
                "findings": "Could not process image at this time.",
                "treatment": "Try taking a clearer photo in better light.",
                "market_risk_impact": "LOW",
                "severity_color": "green"
            }
