from __future__ import annotations

import os

import google.generativeai as genai

from prompts import INITIAL_TRANSLATION_PROMPT, REFINEMENT_PROMPT
from app.engine.pipeline import TranslationPipeline
from app.engine.services.translation import GeminiTranslationService

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def create_pipeline() -> TranslationPipeline:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Cannot initialize translation pipeline.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(DEFAULT_MODEL)
    translator = GeminiTranslationService(
        model,
        INITIAL_TRANSLATION_PROMPT,
        REFINEMENT_PROMPT,
    )
    return TranslationPipeline(translator)
