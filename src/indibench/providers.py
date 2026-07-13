"""Provider-adapter layer (D-042): one `complete()` call for every panel/judge
model family (D-035), keys read from environment variables.

Model-id convention: "<provider>/<model>", e.g.
    openai/gpt-5            -> OPENAI_API_KEY (optional OPENAI_BASE_URL)
    anthropic/claude-...    -> ANTHROPIC_API_KEY
    google/gemini-...       -> GOOGLE_API_KEY
    sarvam/<model>          -> SARVAM_API_KEY + SARVAM_BASE_URL (OpenAI-compatible)

SDKs are imported lazily so the core package needs none of them installed
(`pip install indibench[pipeline]` pulls them in).
"""

import os


def complete(
    model_id: str,
    system: str,
    user: str,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    provider, _, model = model_id.partition("/")
    if not model:
        raise ValueError(f"model_id must be '<provider>/<model>', got {model_id!r}")
    if provider == "openai":
        return _openai_compatible(model, system, user, max_tokens, temperature,
                                  api_key_env="OPENAI_API_KEY", base_url_env="OPENAI_BASE_URL")
    if provider == "sarvam":
        return _openai_compatible(model, system, user, max_tokens, temperature,
                                  api_key_env="SARVAM_API_KEY", base_url_env="SARVAM_BASE_URL")
    if provider == "anthropic":
        return _anthropic(model, system, user, max_tokens, temperature)
    if provider == "google":
        return _google(model, system, user, max_tokens, temperature)
    raise ValueError(f"unknown provider {provider!r} in {model_id!r}")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set — plug in API keys to run this pipeline stage (D-042)"
        )
    return value


def _openai_compatible(model, system, user, max_tokens, temperature,
                       api_key_env, base_url_env) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=_require_env(api_key_env),
                    base_url=os.environ.get(base_url_env) or None)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return response.choices[0].message.content or ""


def _anthropic(model, system, user, max_tokens, temperature) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=_require_env("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _google(model, system, user, max_tokens, temperature) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_require_env("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return response.text or ""
