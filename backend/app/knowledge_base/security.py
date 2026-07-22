# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

# Import standard security, regex, and character normalization libraries
import re
import secrets
import unicodedata


def new_fence_tag(prefix: str = "CTX") -> str:
    """
    Creates a cryptographically random XML tag signature for every chat session.
    This makes it impossible for hackers to guess your context boundaries.
    """
    # Combines your prefix with 12 random hex characters (e.g., 'CTX_a4b2c8f1e3d5')
    return f"{prefix}_{secrets.token_hex(6)}"


# --- UNICODE & OBFUSCATION DETECTORS ---

# List of hidden, zero-width characters attackers use to split bad words (e.g., 'i‌g‌n‌o‌r‌e')
_ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\u2060\ufeff\u00ad"
_ZERO_WIDTH_RE = re.compile(f"[{_ZERO_WIDTH_CHARS}]")

# List of hidden binary control codes that can crash or trick text parsing scripts
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Regex to detect if an attacker is trying to manually type fake XML tags or system boundaries
_FENCE_LOOKALIKE_RE = re.compile(
    r"(</?\s*ctx[_a-z0-9]*\s*>|<\|im_(?:start|end)\|>)|\[\s*system\s*\]", re.IGNORECASE
)


def sanitize_untrusted_text(text: str) -> str:
    """
    Cleanses raw extracted document text or customer messages in RAM memory.
    Strips invisible text, control characters, and flattens formatting.
    """
    if not text:
        return ""

    # Step 1: Normalize Unicode layout (NFKC smashes complex script characters into normal text)
    normalized = unicodedata.normalize("NFKC", text)

    # Step 2: Vaporize all invisible zero-width characters sneakily hidden in words
    normalized = _ZERO_WIDTH_RE.sub("", normalized)

    # Step 3: Strip away background computer control characters
    normalized = _CONTROL_CHARS_RE.sub("", normalized)

    # Step 4: Locate fake context tag attempts and neutralize them into a harmless flag string
    normalized = _FENCE_LOOKALIKE_RE.sub("[removed]", normalized)

    # Step 5: Clean up spacing (Safe ReDoS-protected spacing compression)
    # Using simple regex to collapse white space without catastrophic backtracking
    normalized = re.sub(r"\n\s*\n\s*\n+", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)

    return normalized.strip()


# --- PROMPT INJECTION DETECTORS (BILINGUAL) ---

_SUSPICIOUS_PATTERNS = [
    # English attack variants targeting system prompt rules
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b", re.I
    ),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(?:a|an)\b", re.I),
    re.compile(r"\bsystem\s*prompt\b", re.I),
    re.compile(r"\breveal\s+(?:your|the)\s+(?:system\s+)?prompt\b", re.I),
    # Swahili/Sheng regional attack filters (The East African Guardrail List)
    re.compile(r"\bpuuza\s+maelekezo\b", re.I),  # "Ignore instructions"
    re.compile(r"\bsahau\s+maagizo\b", re.I),  # "Forget directions/orders"
    re.compile(
        r"\bacha\s+kufuata\s+kanuni\b", re.I
    ),  # "Stop following guidelines/rules"
    # Redundant check for bracket block tags
    re.compile(r"</?\s*ctx[_a-z0-9]*\s*>", re.I),
]


def flag_suspicious_upload(text: str) -> list[str]:
    """
    Scans text strings for explicit malicious instruction overrides.
    Returns a list of matching regex rules triggered by the text payload.
    """
    hits: list[str] = []
    # Loop through our structural security gate rules
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(text):
            # Save the triggered rule to alert the application orchestrator
            hits.append(pattern.pattern)
    return hits


# --- INTELLECTUAL PROPERTY & DEEP SECRET SCANNERS ---

_SECRET_PATTERNS = [
    re.compile(r"\bsk-ant-[a-zA-Z0-9_-]{20,}\b"),  # Anthropic/Claude API Tokens
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),  # Standard OpenAI Secret Tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # Amazon Web Services (AWS) Access Keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # Secure RSA/SSL Private Keys
    re.compile(
        r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"
    ),  # JWT Auth Tokens
    re.compile(
        r"\bxox[baprs]-[a-zA-Z0-9-]{10,}\b"
    ),  # Slack Workspace Integration Tokens
]


class EmbeddedSecretError(ValueError):
    """Triggered when corporate cryptographic data is detected inside open text buffers."""

    pass


def assert_no_embedded_secrets(payload: str) -> None:
    """
    Scans compiled payloads right before sending them to the LLM cloud endpoint.
    Guarantees private production server credentials are never accidentally leaked.
    """
    for pattern in _SECRET_PATTERNS:
        if pattern.search(payload):
            # Drop a hard database error and lock down the operation immediately
            raise EmbeddedSecretError(
                "Payload rejected: credential-shaped content detected before LLM call."
            )
