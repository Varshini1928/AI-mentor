from app.prompts import SYSTEM_PROMPT_CODE_GENERATION, build_code_generation_prompt
from app.llm_client import call_groq, DEFAULT_MODEL


def generate_code(prompt: str, language: str, model: str = DEFAULT_MODEL) -> str:
    user_message = build_code_generation_prompt(prompt, language)
    return call_groq(SYSTEM_PROMPT_CODE_GENERATION, user_message, model=model)
