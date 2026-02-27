"""
Groq Explainer — Natural Language Reasoning Layer  (v1.1)

Uses Groq API (Llama 3) to generate human-readable explanations
of the overseer's deterministic decisions.

CRITICAL: This does NOT make decisions. The overseer makes all decisions
deterministically. This only EXPLAINS them in farmer-friendly language.

v1.1 fixes:
  - FIX 2: Structured inputs only — LLM never sees raw data,
           only pre-computed facts. "Do not invent data" enforced.
  - FIX 4: Risk language instead of percentages in all outputs.
  - FIX 6: 2-second timeout — non-blocking. Falls back instantly.
"""

import os
import logging

logger = logging.getLogger('groq_explainer')

# Groq API key — set via environment variable
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_TIMEOUT_SECONDS = 2  # FIX 6: Hard 2-second timeout


def explain_overseer_decision(recommendation, overseer_result):
    """
    Takes the final recommendation and overseer result,
    returns a human-friendly explanation.

    Falls back to templates INSTANTLY if Groq is not available or times out.
    """
    if not GROQ_API_KEY:
        logger.info("Groq API key not set — using template explanations")
        return _template_explanation(recommendation, overseer_result)

    try:
        return _groq_explanation(recommendation, overseer_result)
    except Exception as e:
        logger.warning(f"Groq explanation failed ({type(e).__name__}): {e} — using template fallback")
        return _template_explanation(recommendation, overseer_result)


def _build_structured_input(recommendation, overseer_result):
    """
    FIX 2: Build a STRICT structured input for the LLM.
    Only pre-computed facts — no raw arrays, no model internals, no data the LLM could hallucinate about.
    """
    return {
        'crop': recommendation.get('crop', 'Unknown'),
        'recommendation': recommendation.get('recommendation', 'HOLD'),
        'current_price_inr': round(recommendation.get('current_price_per_quintal', 0)),
        'peak_price_inr': round(recommendation.get('peak_price_per_quintal', 0)),
        'wait_days': recommendation.get('wait_days', 0),
        'risk_level': recommendation.get('risk_level', 'LOW'),
        'verdict': overseer_result.get('verdict', 'APPROVED'),
        'confidence_risk_label': overseer_result.get('confidence_risk_label', 'Moderate reliability'),
        'confidence_risk_message': overseer_result.get('confidence_risk_message', ''),
        'warning_count': overseer_result.get('warning_count', 0),
        'top_warnings': [
            w['message'] for w in overseer_result.get('warnings', [])
            if w.get('severity') in ('high', 'critical')
        ][:3],  # Max 3 high-severity warnings
        'was_overridden': bool(overseer_result.get('overrides')),
        'override_reason': (
            overseer_result['overrides'][0]['reason']
            if overseer_result.get('overrides')
            else None
        ),
    }


def _groq_explanation(recommendation, overseer_result):
    """
    Call Groq API with structured input and strict guardrails.
    Hard 2-second timeout — no blocking.
    """
    import httpx
    from groq import Groq

    # FIX 2: Only pass structured, pre-computed facts
    facts = _build_structured_input(recommendation, overseer_result)

    # Build guardrailed prompt
    system_prompt = (
        "You are a helpful agricultural advisor explaining decisions to Indian farmers. "
        "STRICT RULES:\n"
        "1. Do NOT invent any prices, percentages, or data points.\n"
        "2. Only use the EXACT numbers provided in the input.\n"
        "3. Do NOT generate new recommendations or override the system decision.\n"
        "4. Use simple English. Avoid jargon.\n"
        "5. Use ₹ for all prices.\n"
        "6. Express confidence as reliability, NOT as percentages.\n"
        "7. Keep your response under 80 words.\n"
        "8. Speak directly to the farmer using 'you' and 'your'."
    )

    user_prompt = (
        f"Explain this advice to a farmer:\n\n"
        f"ADVICE: {facts['recommendation']}\n"
        f"CROP: {facts['crop']}\n"
        f"CURRENT PRICE: ₹{facts['current_price_inr']}/quintal\n"
        f"EXPECTED PEAK: ₹{facts['peak_price_inr']}/quintal\n"
        f"WAIT PERIOD: {facts['wait_days']} days\n"
        f"RISK: {facts['risk_level']}\n"
        f"RELIABILITY: {facts['confidence_risk_label']} — {facts['confidence_risk_message']}\n"
        f"WARNINGS: {'; '.join(facts['top_warnings']) if facts['top_warnings'] else 'None'}\n"
    )

    if facts['was_overridden']:
        user_prompt += f"IMPORTANT: The AI safety system changed the advice. Reason: {facts['override_reason']}\n"

    user_prompt += (
        "\nWrite 3-4 sentences explaining:\n"
        "1. What the advice is and why\n"
        "2. The most important warning (if any)\n"
        "3. How reliable this prediction is (use the reliability label, NOT a percentage)\n"
        "4. One simple next step for the farmer"
    )

    # FIX 6: Create client with hard 2-second timeout
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
        temperature=0.2,  # Very low — factual, consistent
        max_tokens=150,   # Hard cap: short response
        top_p=0.9,
    )

    explanation_text = response.choices[0].message.content.strip()

    # FIX 4: Use risk language label, not raw percentage
    return {
        'explanation': explanation_text,
        'source': 'groq',
        'model': GROQ_MODEL,
        'confidence_label': facts['confidence_risk_label'],
        'confidence_message': facts['confidence_risk_message'],
    }


def _template_explanation(recommendation, overseer_result):
    """
    Template-based fallback — instant, no API call.
    Uses risk language throughout (FIX 4).
    """
    verdict = overseer_result.get('verdict', 'APPROVED')
    warnings = overseer_result.get('warnings', [])
    overrides = overseer_result.get('overrides', [])
    risk_label = overseer_result.get('confidence_risk_label', 'Moderate reliability')
    risk_message = overseer_result.get('confidence_risk_message', '')
    crop = recommendation.get('crop', 'Rice')
    rec = recommendation.get('recommendation', 'HOLD')
    current_price = recommendation.get('current_price_per_quintal', 0)
    peak_price = recommendation.get('peak_price_per_quintal', 0)
    wait_days = recommendation.get('wait_days', 0)

    parts = []

    # Main advice
    if rec == 'HOLD' or rec == 'WAIT':
        parts.append(
            f"Our system suggests holding your {crop} for about {wait_days} days. "
            f"Current price is ₹{current_price:.0f}/quintal and we expect it could reach ₹{peak_price:.0f}/quintal."
        )
    else:
        parts.append(
            f"Our system suggests selling your {crop} now at ₹{current_price:.0f}/quintal."
        )

    # Override explanation
    if overrides:
        parts.append(f"Note: {overrides[0]['reason']}")

    # Top warning — risk language only
    high_warnings = [w for w in warnings if w['severity'] in ('high', 'critical')]
    if high_warnings:
        parts.append(f"⚠️ Important: {high_warnings[0]['message']}.")

    # FIX 4: Risk language instead of percentages
    parts.append(f"Prediction reliability: {risk_label.lower()}. {risk_message}.")

    # Verdict-specific note
    if verdict == 'FLAGGED':
        parts.append("This advice has been flagged for review — please verify with local mandi contacts before acting.")
    elif verdict == 'OVERRIDDEN':
        parts.append("The AI safety system has adjusted this advice to protect against potential losses.")

    return {
        'explanation': ' '.join(parts),
        'source': 'template',
        'model': 'rule-based',
        'confidence_label': risk_label,
        'confidence_message': risk_message,
    }
