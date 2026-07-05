"""
Thin client around Groq's OpenAI-compatible chat completions endpoint.

NOTE on model IDs: Groq deprecates model IDs periodically. As of this build,
llama-3.3-70b-versatile and mixtral-8x7b-32768 (the models originally requested)
have been deprecated by Groq. This client defaults to the current recommended
replacements instead:
  - "openai/gpt-oss-120b"  (large, high quality — replacement for llama-3.3-70b-versatile)
  - "openai/gpt-oss-20b"   (smaller, faster)
Always check https://console.groq.com/docs/models before hardcoding model IDs in the future.
"""
import os
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_MODEL = "openai/gpt-oss-120b"
SECONDARY_MODEL = "openai/gpt-oss-20b"
SUPPORTED_MODELS = {DEFAULT_MODEL, SECONDARY_MODEL}

REQUEST_TIMEOUT_SECONDS = 30.0


class GroqClientError(Exception):
    """Raised when the Groq API call fails. Carries a human-readable message."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def call_groq(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise GroqClientError("Server is missing GROQ_API_KEY configuration.", status_code=500)

    if model not in SUPPORTED_MODELS:
        model = DEFAULT_MODEL

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(GROQ_API_URL, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise GroqClientError("The AI provider took too long to respond. Please try again.", status_code=502)
    except httpx.RequestError:
        raise GroqClientError("Could not reach the AI provider. Please try again shortly.", status_code=502)

    if response.status_code == 401:
        raise GroqClientError("AI provider authentication failed (invalid API key).", status_code=502)
    if response.status_code == 429:
        raise GroqClientError("AI provider rate limit reached. Please try again in a moment.", status_code=502)
    if response.status_code >= 400:
        raise GroqClientError(
            f"AI provider returned an error (status {response.status_code}).", status_code=502
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise GroqClientError("AI provider returned an unexpected response format.", status_code=502)
