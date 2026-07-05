from app.prompts import SYSTEM_PROMPT_DEBUGGING, build_debugging_prompt
from app.llm_client import call_groq, DEFAULT_MODEL


def debug_code(code: str, error: str, language: str, model: str = DEFAULT_MODEL) -> str:
    user_message = build_debugging_prompt(code, error, language)
    return call_groq(SYSTEM_PROMPT_DEBUGGING, user_message, model=model)
