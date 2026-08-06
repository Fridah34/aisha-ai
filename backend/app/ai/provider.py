import os
import time

from dotenv import load_dotenv

load_dotenv()

# Cost tracking - switch to Groq when Gemini credit
GEMINI_CREDIT_THRESHOLD = float(os.getenv("GEMINI_CREDIT_THRESHOLD", "10.0"))

# ─── PROVIDER CACHE ──────────────────────────────────────────────────────────
# Cache provider instances to avoid re-initialization on every request
# This dramatically reduces latency for Gemini and Claude calls

_gemini_client = None
_gemini_model = None
_vertexai_initialized = False

_groq_client = None
_claude_client = None


# ─── VERTEX AI INITIALIZATION ──────────────────────────────────────────────
def _init_vertexai():
    """Initialize Vertex AI once at module load or first call."""
    global _vertexai_initialized

    if _vertexai_initialized:
        return

    import vertexai

    vertexai.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0949791582"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    _vertexai_initialized = True
    print("[AISHA] Vertex AI initialized")


def _get_gemini_model(system_instruction: str | None = None):
    """Get or create a Gemini model instance with the given system prompt."""
    from vertexai.generative_models import GenerativeModel

    if not _vertexai_initialized:
        _init_vertexai()

    # Don't cache globally anymore — system_instruction differs per business
    model = GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        system_instruction=system_instruction,
    )
    return model


def _get_groq_client():
    """Get or create a cached Groq client."""
    global _groq_client

    if _groq_client is None:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment")

        _groq_client = Groq(api_key=api_key)
        print("[AISHA] Groq client cached")

    return _groq_client


def _get_claude_client():
    """Get or create a cached Claude client."""
    global _claude_client

    if _claude_client is None:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        _claude_client = anthropic.Anthropic(api_key=api_key)
        print("[AISHA] Claude client cached")

    return _claude_client


# ─── MAIN ENTRY POINT ──────────────────────────────────────────────────────
def get_ai_response(prompt: str, conversation_history: list | None = None) -> str:
    """
    Get AI response with automatic fallback and provider caching.
    """
    if conversation_history is None:
        conversation_history = []

    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()
    start_time = time.time()

    try:
        if AI_PROVIDER == "claude":
            response = _call_claude(prompt, conversation_history)
        elif AI_PROVIDER == "gemini":
            response = _call_gemini(prompt, conversation_history)
        elif AI_PROVIDER == "groq":
            response = _call_groq(prompt, conversation_history)
        else:
            raise ValueError(f"Unknown AI provider: {AI_PROVIDER}")

        elapsed = time.time() - start_time
        print(f"[AISHA] {AI_PROVIDER.upper()} response in {elapsed:.2f}s")
        return response

    except Exception as primary_error:  # noqa: BLE001
        print(f"[AISHA] Primary AI provider '{AI_PROVIDER}' failed: {primary_error}")

        # Auto-fallback to Groq if primary fails
        if AI_PROVIDER != "groq":
            print("[AISHA] Falling back to Groq...")
            try:
                response = _call_groq(prompt, conversation_history)
                elapsed = time.time() - start_time
                print(f"[AISHA] GROQ fallback response in {elapsed:.2f}s")
                return response
            except Exception as fallback_error:  # noqa: BLE001
                print(f"[AISHA] Groq fallback also failed: {fallback_error}")

        return (
            "Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye. "
            "Sorry, we are experiencing a brief issue. Please try again shortly."
        )


# ─── GEMINI IMPLEMENTATION ────────────────────────────────────────────────
def _call_gemini(prompt: str, conversation_history: list) -> str:
    from vertexai.generative_models import Content, Part

    # Get cached model
    model = _get_gemini_model(system_instruction=prompt)

    # Guard - if history is empty, send a default greeting
    if not conversation_history:
        response = model.generate_content("Hello")
        return response.text

    # Build history as Content objects
    history = []
    for msg in conversation_history[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

    # Start a new chat session with the history
    # The system instruction is passed as the first message in the chat
    chat = model.start_chat(history=history)

    # Send the latest message with system prompt prepended
    # This ensures the AI knows the business context
    last_message = conversation_history[-1]["content"]
    response = chat.send_message(last_message)

    return response.text


# ─── CLAUDE IMPLEMENTATION ────────────────────────────────────────────────
def _call_claude(prompt: str, conversation_history: list) -> str:
    """
    Call Claude with cached client.
    """
    client = _get_claude_client()

    response = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=1024,
        system=prompt,
        messages=conversation_history,
    )

    return response.content[0].text


# ─── GROQ IMPLEMENTATION ──────────────────────────────────────────────────
def _call_groq(prompt: str, conversation_history: list) -> str:
    """
    Call Groq with cached client.
    Fastest response times of all three providers.
    """
    client = _get_groq_client()

    # Build messages with system prompt
    messages = [{"role": "system", "content": prompt}] + conversation_history

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )

    return response.choices[0].message.content


# ─── PROVIDER HEALTH CHECK ────────────────────────────────────────────────
def check_provider_health(provider: str | None = None) -> dict:
    """
    Check if a provider is healthy and responding.
    Useful for monitoring and debugging.
    """
    providers_to_check = [provider] if provider else ["gemini", "groq", "claude"]
    results = {}

    for p in providers_to_check:
        try:
            start = time.time()
            if p == "gemini":
                model = _get_gemini_model()
                # Quick test with minimal payload
                response = model.generate_content("Hi")
                results[p] = {
                    "healthy": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "response_preview": response.text[:50],
                }
            elif p == "groq":
                client = _get_groq_client()
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10,
                )
                results[p] = {
                    "healthy": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "response_preview": response.choices[0].message.content[:50],
                }
            elif p == "claude":
                client = _get_claude_client()
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}],
                )
                results[p] = {
                    "healthy": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "response_preview": response.content[0].text[:50],
                }
        except Exception as e:  # noqa: BLE001
            results[p] = {"healthy": False, "error": str(e)}

    return results


# ─── CLEAR CACHE (For testing) ────────────────────────────────────────────
def clear_provider_cache():
    """
    Clear cached provider instances.
    Useful during testing or when configuration changes.
    """
    global _gemini_model, _groq_client, _claude_client, _vertexai_initialized

    _gemini_model = None
    _groq_client = None
    _claude_client = None
    _vertexai_initialized = False

    print("[AISHA] Provider cache cleared")
