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
    temperature: float | None = None,
) -> str:
    """temperature=None (default) omits the parameter — GPT-5-class reasoning
    models reject non-default temperatures, so callers opt in explicitly."""
    provider, _, model = model_id.partition("/")
    if not model:
        raise ValueError(f"model_id must be '<provider>/<model>', got {model_id!r}")
    if provider == "openai":
        return _openai_compatible(model, system, user, max_tokens, temperature,
                                  api_key_env="OPENAI_API_KEY", base_url_env="OPENAI_BASE_URL",
                                  token_param="max_completion_tokens")
    if provider == "sarvam":
        return _openai_compatible(model, system, user, max_tokens, temperature,
                                  api_key_env="SARVAM_API_KEY", base_url_env="SARVAM_BASE_URL",
                                  token_param="max_tokens")
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
                       api_key_env, base_url_env, token_param) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=_require_env(api_key_env),
                    base_url=os.environ.get(base_url_env) or None)
    kwargs = {token_param: max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        **kwargs,
    )
    return response.choices[0].message.content or ""


def _anthropic(model, system, user, max_tokens, temperature) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=_require_env("ANTHROPIC_API_KEY"))
    kwargs = {} if temperature is None else {"temperature": temperature}
    response = client.messages.create(
        model=model,
        system=system,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": user}],
        **kwargs,
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
            **({} if temperature is None else {"temperature": temperature}),
        ),
    )
    return response.text or ""
