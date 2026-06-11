def estimate_tokens(text: str) -> int:
    """
    Estimates token count for a piece of text.

    Why estimate and not count exactly?
    Exact token counting requires the tokenizer library
    for each specific model — adds complexity and dependencies.
    A good estimate is: 1 token ≈ 4 characters in English,
    1 token ≈ 3 characters in Swahili (more characters per word).
    We use 4 as a safe average for mixed content.
    """
    return len(text) // 4


def truncate_history_to_token_limit(
    history: list,
    system_prompt: str,
    max_total_tokens: int = 6000,
    max_messages : int =20
) -> list:
    """
    Strategy: always keep the most recent messages.
    Drop oldest messages first — they are least relevant
    to the current conversation context.
    """
    # Calculate tokens already used by system prompt
    used_tokens = estimate_tokens(system_prompt)
    available = max_total_tokens - used_tokens

    if available <= 0:
        # System prompt itself is too long — return empty history
        print("Warning: system prompt exceeds token budget")
        return []

    # Work backwards from most recent message
    # keeping messages until we hit the token limit
    kept_messages = []
    tokens_used = 0

    for message in reversed(history):
        if len(kept_messages) >= max_messages:
            break
        message_tokens = estimate_tokens(message["content"])
        if tokens_used + message_tokens > available:
            break
        kept_messages.insert(0, message)
        tokens_used += message_tokens

    original_count = len(history)
    kept_count = len(kept_messages)

    if kept_count < original_count:
        print(
            f"History truncated: kept {kept_count} of "
            f"{original_count} messages to fit token budget"
        )

    return kept_messages