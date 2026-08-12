import re
import uuid

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.ai import cache
from app.ai.provider import get_ai_response
from app.ai.token_utils import truncate_history_to_token_limit
from app.handover import HandoverService
from app.knowledge_base.manager import KnowledgeBaseManager
from app.models import (
    Category,
    Conversation,
    ConversationState,
    Customer,
    HandoverStatus,
    Language,
    MessageRole,
    Product,
    User,
)

SWITCH_HINT = "\n\n_Reply 'menu' to browse other stores anytime._"

# Emitted by the AI itself (as instructed in SYSTEM_PROMPT_SUFFIX below)
# when the customer's message isn't a real question it can meaningfully
# answer — e.g. noise, a stray word, or an attempt at a menu selection
# that slipped through. Same mechanism as [HANDOVER_REQUIRED] and
# [SHOW_CATEGORIES] below: a tag the model puts in its own output that
# our code detects and strips before the customer ever sees it.
#
# This REPLACES the old approach of pre-filtering with a hardcoded
# keyword list (BUSINESS_QUESTION_KEYWORDS in marketplace_flow.py) before
# ever calling the AI. That list could only ever catch phrasings someone
# had already thought to add — real customers kept finding phrasings
# ("what time do you guys open?") that weren't in it, and got a flat
# "sorry, I didn't understand" instead of an answer. Now the AI is always
# asked (for anything that isn't pure noise — see router.py's
# _is_negligible_input) and decides FOR ITSELF whether it has a
# meaningful answer, using its actual understanding of the message
# rather than string matching.
NOT_UNDERSTOOD_TAG = "[NOT_UNDERSTOOD]"

# Appended to every business's system prompt after it's built/cached
# (see get_business_prompt below). Two jobs:
#   1. Tells the model when to emit NOT_UNDERSTOOD_TAG instead of
#      guessing at an answer to noise/menu-selection text.
#   2. Fixes the "AI hedges instead of using data it already has"
#      pattern — e.g. a customer asking for a size that isn't listed
#      getting "it doesn't specify size availability, would you like me
#      to check?" instead of just stating the sizes that ARE listed,
#      which were sitting right there in the product data the whole
#      time.
#
# Appended in service.py rather than folded into build_system_prompt()
# so it always applies — including to prompts already cached in Redis by
# get_business_prompt() — without needing a cache-bust when this wording
# changes. If build_system_prompt already carries similar instructions,
# this reinforces rather than conflicts with them.
SYSTEM_PROMPT_SUFFIX = (
    "\n\n---\n"
    f"If the customer's message is NOT a real question and not something "
    f"you can meaningfully respond to — e.g. it looks like noise, a "
    f"stray word or character, or an attempt to pick a product/size/"
    f"quantity/menu option rather than ask something — reply with ONLY "
    f"the exact tag {NOT_UNDERSTOOD_TAG} and nothing else. Do not guess "
    f"at an answer in that case.\n\n"
    "Otherwise, answer normally using the product data and knowledge "
    "base above. If you don't have an exact answer for what was asked, "
    "do not just say you don't know or ask a vague follow-up question. "
    "Instead:\n"
    "1. Check if there is a closely related fact you DO have (e.g. if "
    "asked for a size that isn't listed, state the sizes that ARE listed; "
    "if asked about a color/flavor that isn't listed, state what IS "
    "available), and lead with that.\n"
    "2. Only if there is truly nothing related in the data, say so "
    "plainly and offer to connect them with the team — do not guess or "
    "invent details that aren't in the product data or knowledge base."
)

SWAHILI_INDICATORS = {
    # greetings
    "habari",
    "mambo",
    "salama",
    "hujambo",
    "hamjambo",
    # commerce
    "ninataka",
    "nataka",
    "nunua",
    "kununua",
    "bei",
    "gharama",
    "lipa",
    "malipo",
    "mpesa",
    "order",
    "niorder",
    "bidhaa",
    "inapatikana",
    "stock",
    "tuma",
    "delivery",
    "ongea",
    # confirmations
    "ndiyo",
    "ndio",
    "hapana",
    "sawa",
    "sawa sawa",
    "asante",
    "karibu",
    "tafadhali",
    "samahani",
    "pole",
    "ngoja",
    # questions
    "nini",
    "wapi",
    "lini",
    "vipi",
    "kwa nini",
    "ngapi",
    # products / sizes
    "saizi",
    "rangi",
    "nyekundu",
    "nyeupe",
    "nyeusi",
    "kubwa",
    "ndogo",
    # pronouns / common words
    "mimi",
    "wewe",
    "yeye",
    "sisi",
    "wao",
    "tuna",
    "nina",
    "yake",
    "yangu",
    "yenu",
    "hii",
    "hiyo",
    "hizo",
}

NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

# Handover urgency keywords
URGENT_KEYWORDS = {
    # English
    "complaint",
    "refund",
    "scam",
    "fraud",
    "angry",
    "terrible",
    "wrong",
    "broken",
    "missing",
    "stolen",
    "cheat",
    "lied",
    # Kiswahili
    "malalamiko",
    "rudisha pesa",
    "uongo",
    "hasira",
    "mbaya sana",
    "ilinibidi",
    "nilidanganywa",
    "tatizo kubwa",
}


async def build_prompt_from_context(
    business_id: uuid.UUID, merchant_name: str, async_session: AsyncSession
) -> str:
    """
    Build system prompt using KnowledgeBaseManager to retrieve from wiki_chunks.
    Checks Redis cache first, then builds fresh prompt on miss.
    """
    cached = cache.get_cached_business_prompt(business_id)
    if cached:
        print(f"[Cache HIT] Business {business_id} prompt from redis")
        return cached

    print(f"[Cache MISS] Building prompt for business {business_id} from knowledge base")

    manager = KnowledgeBaseManager(session=async_session)

    payload = await manager.build_prompt_payload(
        business_id=business_id,
        merchant_name=merchant_name,
        customer_message="",
    )

    prompt = manager.render_and_verify(payload)
    cache.cache_business_prompt(business_id, prompt)

    return prompt


def get_conversation_history(
    customer_id: uuid.UUID, business_id: uuid.UUID, db: Session, limit: int = 10
) -> list:
    """Fetch conversation history from Redis cache or PostgreSQL."""

    # Step 1 — check Redis first
    cached = cache.get_cached_conversation(customer_id, business_id)
    if cached is not None:
        print("[Cache HIT] Conversation from Redis")
        return cached

    # Step 2 — cache miss, fetch from PostgreSQL
    print("[Cache MISS] Fetching conversation from PostgreSQL")

    messages = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.business_id == business_id,
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )

    messages = list(reversed(messages))

    history = []
    for msg in messages:
        role = "user" if msg.role == MessageRole.Customer else "assistant"
        history.append({"role": role, "content": msg.content})

    # Remove any leading assistant messages (conversations should start with user)
    while history and history[0]["role"] != "user":
        history.pop(0)

    # Step 3 - store in Redis for next time
    cache.cache_conversation(customer_id, business_id, history)

    return history


def save_message(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    role: str,
    content: str,
    language: str,
    db: Session,
    delivery_status: str | None = None,
) -> None:
    """Save a message to PostgreSQL and update Redis cache."""

    ROLE_MAP = {
        "user": MessageRole.Customer,
        "customer": MessageRole.Customer,
        "assistant": MessageRole.Assistant,
        "human": MessageRole.Human,
    }

    LANGUAGE_MAP = {"EN": Language.en, "SW": Language.sw}

    # saves to PostgreSQL permanently and updates Redis simultaneously
    new_message = Conversation(
        customer_id=customer_id,
        business_id=business_id,
        role=ROLE_MAP[role.lower()],
        content=content,
        language=LANGUAGE_MAP.get(language.upper(), Language.en),
        delivery_status=delivery_status,
    )
    db.add(new_message)
    db.commit()

    # Update Redis cache immediately
    history_role = "user" if role.lower() in ("user", "customer") else "assistant"
    cache.append_to_conversation_cache(
        customer_id=customer_id,
        business_id=business_id,
        message={"role": history_role, "content": content},
    )


def normalize_phone(phone_number: str) -> str:
    """Normalize WhatsApp phone numbers to consistent format."""
    phone = phone_number.strip()
    phone = phone.removeprefix("whatsapp:")
    phone = phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


def get_or_create_customer(
    phone_number: str, business_id: uuid.UUID, db: Session, profile_name: str | None = None
) -> Customer:
    """Find a customer by phone number or create them if first message."""
    # Phone number is the customer's only identity — no accounts needed.
    # Normalizes the number before lookup to prevent duplicate records.

    phone = normalize_phone(phone_number)

    customer = (
        db.query(Customer)
        .filter(Customer.phone_number == phone, Customer.business_id == business_id)
        .first()
    )

    if not customer:
        customer = Customer(phone_number=phone, business_id=business_id, name=profile_name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
        print(f"[AISHA] New customer registered: {phone} ({profile_name or 'no name'})")
    else:
        customer.last_seen = func.now()
        if profile_name and not customer.name:
            customer.name = profile_name
        db.commit()

    return customer


def detect_handover(response: str) -> bool:
    """Check if response contains handover tag."""
    return "[HANDOVER_REQUIRED]" in response


def detect_category_browse_request(response: str) -> bool:
    """
    True when AISHA decided (via the system prompt instruction) that the customer wants to browse generally rather than asking about something specific.
    Uses same mechanism as detect_handover — a tag the LLM emits, stripped later by clean_response() before the customer sees it.
    """
    return "[SHOW_CATEGORIES]" in response


def detect_not_understood(response: str) -> bool:
    """True when the AI emitted NOT_UNDERSTOOD_TAG — its own signal that
    the customer's message wasn't a real question it could meaningfully
    answer (noise, a menu-selection attempt, etc). Checked the same way
    as detect_handover/detect_category_browse_request: a plain substring
    check on the raw (not-yet-tag-stripped) response. See
    SYSTEM_PROMPT_SUFFIX for the instruction that produces this tag, and
    process_customer_message for how callers (router.py) use the
    resulting "not_understood" flag to fall back to deterministic
    flow-specific replies instead of showing a hedgy AI answer."""
    return NOT_UNDERSTOOD_TAG in response


def classify_handover_urgency(customer_message: str) -> str:
    """Classify handover urgency based on message keywords."""
    text_lower = customer_message.lower()
    if any(keyword in text_lower for keyword in URGENT_KEYWORDS):
        return "urgent"
    return "normal"


def clean_response(response: str) -> str:
    """
    Strips internal tags before sending response to customer.
    Customers must never see system tags in their WhatsApp chat.
    """
    response = response.replace("[HANDOVER_REQUIRED]", "")
    response = response.replace("[SHOW_CATEGORIES]", "")
    response = response.replace(NOT_UNDERSTOOD_TAG, "")
    response = re.sub(r"\(.*?handover.*?\)", "", response, flags=re.IGNORECASE)
    return response.strip()


def detect_language(text: str) -> str:
    """Detect whether text is English or Swahili."""
    text_lower = text.lower().strip()
    words = set(text_lower.split())

    if words.intersection(SWAHILI_INDICATORS):
        return "SW"
    if any(indicator in text_lower for indicator in SWAHILI_INDICATORS):
        return "SW"
    return "EN"


def get_categories_for_business(business_id: uuid.UUID, db: Session) -> list:
    """Active categories for a business, in the order the owner wants them shown."""
    return (
        db.query(Category)
        .filter(Category.business_id == business_id, Category.is_active.is_(True))
        .order_by(Category.display_order, Category.name)
        .all()
    )


def format_category_list(categories: list) -> str:
    """
    Builds a plain-text WhatsApp message that looks like tappable buttons
    using bold + numbered emoji. This is the free-form substitute for a real
    Twilio interactive List Message.
    """
    lines = ["Which category are you shopping for today? 🛍️", ""]
    for i, cat in enumerate(categories):
        emoji = NUMBERS[i] if i < len(NUMBERS) else f"{i + 1}."
        lines.append(f"{emoji} *{cat.name}*")
    lines.append("")
    lines.append("Just reply with a number or the category name.")
    return "\n".join(lines)


def match_category_selection(message_text: str, categories: list) -> Category | None:
    """
    Deterministic match of a customer's reply against the category list they
    were just shown. Tried before falling back to the LLM — cheap, instant,
    and can't hallucinate a category that doesn't exist.
    """
    text = message_text.strip().lower()

    # Numeric match: "2", "2.", "option 2", emoji digit copy-pasted back, etc.
    digits = re.sub(r"[^\d]", "", text)
    if digits.isdigit():
        index = int(digits) - 1
        if 0 <= index < len(categories):
            return categories[index]

    # Name match: exact or the category name appears in what they typed
    for cat in categories:
        name_lower = cat.name.strip().lower()
        if name_lower == text or name_lower in text:
            return cat

    return None


def format_products_in_category(products: list) -> str:
    """Plain-text product list sent after a customer picks a category."""
    if not products:
        return (
            "We don't have items in that category right now — "
            "want to see something else?"
        )

    lines = ["Here's what we have:", ""]
    for p in products:
        line = f"• *{p.name}* — Ksh {p.price}"
        if p.unit:
            line += f" / {p.unit}"
        lines.append(line)
    lines.append("")
    lines.append("Want details on any of these, or ready to order?")
    return "\n".join(lines)


async def process_customer_message(
    phone_number: str,
    message_text: str,
    business_id: uuid.UUID,
    db: Session,
    async_db: AsyncSession | None = None,
    profile_name=None,
) -> dict:
    """Main orchestrator — called by the WhatsApp webhook on every incoming customer message."""
    # 1. Find or create customer
    customer = get_or_create_customer(phone_number,business_id, db, profile_name)

    # 2. Detect language for logging
    language = detect_language(message_text)

    # NOTE: the customer's message is NOT saved here. message_processor.py
    # (this function's only caller, both via _ask_ai() and the bottom
    # AI fall-through) already saves it, unconditionally, before this
    # function is ever invoked — saving it again here duplicated every
    # customer message in the conversation log. Step 6 below already
    # handles the case where `history` (fetched from cache/DB) doesn't
    # yet reflect the just-saved message, so removing this doesn't
    # change what the AI sees — it only stops the double DB write.
    # If process_customer_message() ever gains a second caller that
    # DOESN'T already save the user's message upstream, this needs to
    # move back or be made conditional.

    state = get_or_create_conversation_state(customer.id, business_id, db)

    # NEEDS_HUMAN / HUMAN_ACTIVE / RESOLVED are informational for the
    # dashboard only — they are NOT a gate here. This function used to
    # short-circuit with a fixed "you're connected with our team" reply
    # whenever status was HUMAN_ACTIVE/NEEDS_HUMAN, before the message
    # was even looked at — that's why every customer message got back
    # an identical canned string regardless of what they actually said,
    # and why the conversation could never move forward until an owner
    # resolved it from the dashboard. AISHA now answers every message
    # normally no matter the status. The owner's own reply path
    # (send_manual_reply in the conversations router) is a completely
    # separate code path from this one, so there's no risk of AISHA
    # talking over a live human reply by removing this gate — see the
    # matching comment on the handover gate in message_processor.py.
    if state.status == HandoverStatus.RESOLVED:
        # A new message after the owner closed it out — AI resumes.
        state.status = HandoverStatus.AI_ACTIVE
        db.commit()

    # 3.5 If we're waiting on a category selection, try to resolve it
    #     deterministically before spending an LLM call on it.
    if (
        hasattr(state, "pending_action")
        and state.pending_action == "category_selection"
    ):
        categories = get_categories_for_business(business_id, db)
        matched = match_category_selection(message_text, categories)

        if matched:
            state.pending_action = None
            db.commit()

            products_in_category = (
                db.query(Product)
                .filter(
                    Product.business_id == business_id,
                    Product.category_id == matched.id,
                    Product.is_available.is_(True),
                )
                .all()
            )
            reply = format_products_in_category(products_in_category)

            save_message(
                customer_id=customer.id,
                business_id=business_id,
                role="assistant",
                content=reply,
                language=language,
                db=db,
            )

            return {
                "response": reply,
                "needs_handover": False,
                "handover_urgency": None,
                "customer_id": customer.id,
                "language": language,
                "response_language": language,
                "ai_responded": True,
                "not_understood": False,
            }
        else:
            # No clean match — clear the flag and let the normal LLM flow handle it
            state.pending_action = None
            db.commit()

    # 4. Build prompt from knowledge base
    if async_db is None:
        raise ValueError("async_db parameter is required for knowledge base retrieval")

    user = db.query(User).filter(User.id == business_id).first()
    if not user:
        raise ValueError(f"Business owner with id {business_id} not found")

    system_prompt = await build_prompt_from_context(
        business_id=business_id,
        merchant_name=user.business_name,
        async_session=async_db,
    )

    # 4b. Append the not-understood + grounding instructions so the model
    # (a) tells us plainly when it can't meaningfully answer, via
    # NOT_UNDERSTOOD_TAG, instead of us guessing that with a keyword
    # list, and (b) prefers "here's the closest related answer I DO
    # have" over hedging when the exact fact isn't in the product data
    # or knowledge base. See SYSTEM_PROMPT_SUFFIX docstring above for why
    # this is appended here rather than baked into build_system_prompt().
    system_prompt = system_prompt + SYSTEM_PROMPT_SUFFIX

    # 5. Fetch conversation history from database
    history = get_conversation_history(customer.id, business_id, db)

    history = truncate_history_to_token_limit(history, system_prompt)

    # 6. Ensure current message is at the end of history
    if not history or history[-1]["content"] != message_text:
        history.append({"role": "user", "content": message_text})

    # 7. Get AI response
    raw_response = get_ai_response(system_prompt, history)

    # 8. Parse language tag and clean response in one step
    detected_language, clean = parse_ai_response(raw_response)

    # 9. Check for handover trigger
    needs_handover = detect_handover(clean)

    # 9b. Check whether AISHA wants to show the category picker
    show_categories = detect_category_browse_request(clean)

    # 9c. Check whether AISHA is signaling it couldn't meaningfully
    # answer this message. Checked on `clean` (post language-tag-strip,
    # pre other-tag-strip) same as the two checks above — must happen
    # BEFORE clean_response() removes the tag below.
    not_understood = detect_not_understood(clean)

    # 10. Clean internal tags from response
    clean = clean_response(clean)

    # 10b. If AISHA asked to show categories (and isn't simultaneously handing over),
    #      append the category list and mark the state for next reply.
    if show_categories and not needs_handover:
        categories = get_categories_for_business(business_id, db)
        if categories:
            category_text = format_category_list(categories)
            clean = f"{clean}\n\n{category_text}" if clean else category_text
            state.pending_action = "category_selection"
            db.commit()

    # 11. Classify handover urgency (used by dashboard prioritization)
    urgency = classify_handover_urgency(message_text) if needs_handover else None

    # 12. Save AISHA's response. Deliberately still saved to the
    # conversation log even when not_understood is True (clean will just
    # be empty/near-empty after tag-stripping) — callers in router.py
    # send their OWN fallback text to the customer and log that
    # separately via _send_fallback_reply, so this save is only about
    # keeping the transcript honest about what the AI actually returned.
    save_message(
        customer_id=customer.id,
        business_id=business_id,
        role="assistant",
        content=clean,
        language=detected_language,
        db=db,
    )

    if needs_handover:
        state.status = HandoverStatus.NEEDS_HUMAN
        db.commit()
        notify_handover(
            customer.id, business_id, message_text, urgency, db,
            conversation_id=state.id, ai_summary=clean,
        )

    return {
        "response": clean,
        "needs_handover": needs_handover,
        "handover_urgency": urgency,
        "customer_id": customer.id,
        "language": language,
        "response_language": detected_language,
        "ai_responded": True,
        "not_understood": not_understood,
    }


def notify_handover(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    customer_message: str,
    urgency: str,
    db: Session,
    *,
    conversation_id: uuid.UUID,
    ai_summary: str | None = None,
) -> None:
    """
    Creates the HandoverEvent audit row and dispatches notifications across
    every channel the business has enabled (Dashboard/WhatsApp/Email), each
    respecting its own configured delay. See app/handover/handover_service.py.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    phone = customer.phone_number if customer else "unknown"
    customer_name = customer.name if customer else None

    HandoverService.create_event_and_notify(
        db,
        business_id=business_id,
        conversation_id=conversation_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=phone,
        customer_last_message=customer_message,
        ai_summary=ai_summary,
        reason=f"[{urgency.upper()}] {customer_message[:200]}" if urgency else customer_message,
    )


def get_or_create_conversation_state(
    customer_id: uuid.UUID, business_id: uuid.UUID, db: Session
) -> ConversationState:
    """Get or create conversation state for a customer."""
    state = (
        db.query(ConversationState)
        .filter(
            ConversationState.customer_id == customer_id,
            ConversationState.business_id == business_id,
        )
        .first()
    )
    if not state:
        state = ConversationState(customer_id=customer_id, business_id=business_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def parse_ai_response(raw_response: str) -> tuple:
    """
    Parses the AI's self-tagged response into language and clean text.
    Expects format: [LANG:en]\nResponse text
    Falls back to language detection if tag is missing.
    """
    if not raw_response:
        return "EN", ""

    lines = raw_response.strip().split("\n", 1)
    first_line = lines[0].strip()

    # Happy path - AI included the language tag correctly
    if first_line == "[LANG:en]":
        clean = lines[1].strip() if len(lines) > 1 else ""
        return "EN", clean

    if first_line == "[LANG:sw]":
        clean = lines[1].strip() if len(lines) > 1 else ""
        return "SW", clean

    # Fallback — AI forgot the tag (happens occasionally)
    # Use simple word check rather than a library
    print("[AISHA WARNING] AI response missing language tag — using word fallback")
    language = detect_language(raw_response)
    return language, raw_response.strip()

