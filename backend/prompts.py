# backend/prompts.py

INITIAL_TRANSLATION_PROMPT = """Translate the following Lao text into natural, fluent, and idiomatic Korean.
Provide the Korean translation. Do not include the original Lao text.
Format the entire output using Markdown for optimal readability, including headings, lists, and paragraphs as appropriate.
Focus on direct and accurate translation, avoiding any additional explanations, descriptions, or interpretations.

Lao Text to Translate:
{extracted_text}

Korean Translation:"""

REFINEMENT_PROMPT = """The following Korean text was translated from Lao.
Please review and refine it to ensure it is a direct, natural-sounding, and idiomatic Korean translation.
Provide the refined Korean translation. Do not include the original Lao text or any explanations.
Ensure the entire output is well-formatted using Markdown, improving readability with appropriate headings, lists, and paragraphs.

Korean Text to Refine:
{translated_text}

Refined Korean Translation:"""
