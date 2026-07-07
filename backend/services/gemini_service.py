from __future__ import annotations

import json
import os
import re
from typing import Any


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned_text = text.strip()
    cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError:
        start = cleaned_text.find("{")
        end = cleaned_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(cleaned_text[start : end + 1])
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None


def generate_gemini_analysis(prompt: str) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
        response_text = getattr(response, "text", "") or ""
        parsed = _extract_json(response_text)
        if parsed is not None:
            return parsed
    except Exception:
        return None

    return None
