import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class GeminiTranslationService:
    def __init__(
        self,
        model,
        initial_prompt_template: str,
        refinement_prompt_template: str,
    ) -> None:
        self._model = model
        self._initial_prompt_template = initial_prompt_template
        self._refinement_prompt_template = refinement_prompt_template

    def translate(
        self,
        extracted_text: str,
        task_id: str,
        on_refinement: Optional[Callable[[], None]] = None,
    ) -> str:
        max_input_chunk_chars = 20000
        translated_chunks: List[str] = []
        current_pos = 0

        while current_pos < len(extracted_text):
            logger.info(
                "[Task %s] Chunking: current_pos=%d/%d",
                task_id,
                current_pos,
                len(extracted_text),
            )
            max_chunk_end = min(current_pos + max_input_chunk_chars, len(extracted_text))
            break_point = -1

            double_newline_idx = extracted_text.rfind("\n\n", current_pos, max_chunk_end)
            if double_newline_idx != -1:
                break_point = double_newline_idx + 2

            if break_point == -1:
                period_idx = extracted_text.rfind(".", current_pos, max_chunk_end)
                if period_idx != -1:
                    break_point = period_idx + 1

            if break_point <= current_pos or break_point == -1:
                break_point = max_chunk_end

            if break_point == current_pos and current_pos < len(extracted_text):
                break_point = min(current_pos + 1, len(extracted_text))

            logger.info(
                "[Task %s] Chunking: max_chunk_end=%d, break_point=%d",
                task_id,
                max_chunk_end,
                break_point,
            )
            chunk = extracted_text[current_pos:break_point]

            if not chunk.strip():
                logger.info(
                    "[Task %s] Skipping empty/whitespace chunk at current_pos=%d",
                    task_id,
                    current_pos,
                )
                current_pos = break_point
                continue

            try:
                logger.info(
                    "[Task %s] Translating chunk (length: %d characters)...",
                    task_id,
                    len(chunk),
                )
                prompt = self._initial_prompt_template.format(extracted_text=chunk)
                response = self._model.generate_content(prompt)

                if not getattr(response, "candidates", None):
                    logger.error(
                        "[Task %s] Initial translation failed for chunk: No candidates returned.",
                        task_id,
                    )
                    raise ValueError("Gemini API initial translation failed for chunk: No candidates returned.")

                translated_chunks.append(response.text)
                logger.info(
                    "[Task %s] Chunk translation successful. Translated text length: %d characters.",
                    task_id,
                    len(response.text or ""),
                )

            except Exception as exc:  # pragma: no cover - API failure path
                logger.error(
                    "[Task %s] Gemini API translation failed for chunk: %s",
                    task_id,
                    exc,
                )
                raise ValueError(f"Gemini API translation failed for chunk: {exc}") from exc

            current_pos = break_point
            if current_pos == len(extracted_text) and break_point < len(extracted_text):
                current_pos = len(extracted_text)

        full_translated_text = "".join(translated_chunks)
        logger.info(
            "[Task %s] All chunks translated. Total translated text length: %d characters.",
            task_id,
            len(full_translated_text),
        )
        logger.info(
            "[Task %s] Length of text for refinement: %d characters.",
            task_id,
            len(full_translated_text),
        )

        if on_refinement:
            on_refinement()

        refinement_prompt = self._refinement_prompt_template.format(
            translated_text=full_translated_text
        )
        try:
            logger.info("[Task %s] Calling Gemini API for refinement...", task_id)
            refinement_response = self._model.generate_content(refinement_prompt)
            logger.info("[Task %s] Gemini API refinement response received.", task_id)
        except Exception as exc:  # pragma: no cover - API failure path
            raise ValueError(f"Gemini API refinement failed: {exc}") from exc

        if not getattr(refinement_response, "candidates", None):
            logger.error("[Task %s] Refinement failed: No candidates returned.", task_id)
            raise ValueError("Gemini API refinement failed: No candidates returned.")

        translated_text = refinement_response.text
        logger.info(
            "[Task %s] Translation refinement successful. Refined text length: %d characters.",
            task_id,
            len(translated_text or ""),
        )
        return translated_text or ""
