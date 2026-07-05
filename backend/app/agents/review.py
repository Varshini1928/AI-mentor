from typing import Optional

from app.prompts import SYSTEM_PROMPT_CODE_REVIEW, build_code_review_prompt
from app.llm_client import call_groq, DEFAULT_MODEL


def review_code(
    code: str,
    language: str,
    model: str = DEFAULT_MODEL,
    retrieved_context: Optional[str] = None,
) -> str:
    user_message = build_code_review_prompt(code, language, retrieved_context=retrieved_context)
    return call_groq(SYSTEM_PROMPT_CODE_REVIEW, user_message, model=model)
