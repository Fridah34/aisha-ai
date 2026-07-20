import uuid
import re

from app.ai import cache
from app.ai.prompt_builder import build_system_prompt
from app.ai.provider import get_ai_response
from app.ai.token_utils import truncate_history_to_token_limit
from app.models import (
    Category,
    Conversation,
    ConversationState,
    Customer,
    HandoverStatus,
    MessageRole,
    Product,
    User,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

SWITCH_HINT = "\n\n_Reply 'menu' to browse other stores anytime._"

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


def get_business_prompt(business_id: uuid.UUID, db: Session) -> str:
    """Build system prompt from business data, checking Redis cache first."""
    # Step 1 - check Redis first
    cached = cache.get_cached_business_prompt(business_id)
    if cached:
        print(f"[Cache HIT] Business {business_id} prompt from redis")
        return cached

    # Step 2 - cache miss, fetch from PostgreSQL
    print(f"[Cache MISS] Fetching business {business_id} from PostgreSQL")

    user = db.query(User).filter(User.id == business_id).first()
    if not user:
        raise ValueError(f"Business owner with id {business_id} not found")

    products = (
        db.query(Product)
        .filter(Product.business_id == business_id)
        .filter(Product.is_available.is_(True))
        .all()
    )

    products_list = [
        {
            "name": p.name,
            "price": float(p.price),
            "is_available": p.is_available,
            "description": p.description,
            "category": p.category,
            "variant_label": p.variant_label,
            "variant_options": p.variant_options,
            "unit": p.unit,
            "upsell_text": p.upsell_text,
            "image_url": p.image_url,
        }
        for p in products
    ]

    # Fetch knowledge base for the business
    knowledge_base = user.knowledge_base_text or ""
    business_type = getattr(user, "business_type", "retail") or "retail"

    prompt = build_system_prompt(
        business_name=user.business_name,
        products=products_list,
        knowledge_base=knowledge_base,
        business_type=business_type,
    )

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
        role = "user" if msg.role == MessageRole.USER else "assistant"
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

    # saves to PostgreSQL permanently and updates Redis simultaneously
    new_message = Conversation(
        customer_id=customer_id,
        business_id=business_id,
        role=MessageRole(role.upper()),
        content=content,
        language=language,
        delivery_status=delivery_status,
    )
    db.add(new_message)
    db.commit()

    # Update Redis cache immediately
    history_role = "user" if role.upper() == MessageRole.USER.value else "assistant"
    cache.append_to_conversation_cache(
        customer_id=customer_id,
        business_id=business_id,
        message={"role": history_role, "content": content},
    )


def normalize_phone(phone_number: str) -> str:
    """Normalize WhatsApp phone numbers to consistent format."""
    phone = phone_number.strip()
    if phone.startswith("whatsapp:"):
        phone = phone[len("whatsapp:") :]
    phone = phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


def get_or_create_customer(
    phone_number: str, db: Session, profile_name: str | None = None
) -> Customer:
    """Find a customer by phone number or create them if first message."""
    # Phone number is the customer's only identity — no accounts needed.
    # Normalizes the number before lookup to prevent duplicate records.

    phone = normalize_phone(phone_number)

    customer = db.query(Customer).filter(Customer.phone_number == phone).first()

    if not customer:
        customer = Customer(phone_number=phone, name=profile_name)
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


def process_customer_message(
    phone_number: str,
    message_text: str,
    business_id: uuid.UUID,
    db: Session,
    profile_name=None,
) -> dict:
    """Main orchestrator — called by the WhatsApp webhook on every incoming customer message."""
    # 1. Find or create customer
    customer = get_or_create_customer(phone_number, db, profile_name)

    # 2. Detect language for logging
    language = detect_language(message_text)

    # 3. Save customer message
    save_message(
        customer_id=customer.id,
        business_id=business_id,
        role="user",
        content=message_text,
        language=language,
        db=db,
    )

    state = get_or_create_conversation_state(customer.id, business_id, db)

    if state.status in (HandoverStatus.HUMAN_ACTIVE, HandoverStatus.NEEDS_HUMAN):
        # Customer is already with a human; send acknowledgment instead of silence
        waiting_msg = "You're connected with our team — they'll be with you shortly!"
        save_message(
            customer_id=customer.id,
            business_id=business_id,
            role="assistant",
            content=waiting_msg,
            language=language,
            db=db,
        )
        return {
            "response": waiting_msg,
            "needs_handover": True,
            "ai_responded": False,
            "customer_id": customer.id,
            "language": language,
        }

    # A new message after the owner closed it out — AI resumes.
    if state.status == HandoverStatus.RESOLVED:
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
            }
        else:
            # No clean match — clear the flag and let the normal LLM flow handle it
            state.pending_action = None
            db.commit()

    # 4. Build prompt from real database data
    system_prompt = get_business_prompt(business_id, db)

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

    # 12. Save AISHA's response
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
        notify_handover(customer.id, business_id, message_text, urgency, db)

    return {
        "response": clean,
        "needs_handover": needs_handover,
        "handover_urgency": urgency,
        "customer_id": customer.id,
        "language": language,
        "response_language": detected_language,
        "ai_responded": True,
    }


def notify_handover(
    customer_id: uuid.UUID,
    business_id: uuid.UUID,
    customer_message: str,
    urgency: str,
    db: Session,
) -> None:
    """
    Alerts when AISHA triggers a handover.
    Logs to console. Dashboard picks up needs_human conversations via polling/websocket.
    """
    user = db.query(User).filter(User.id == business_id).first()
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    phone = customer.phone_number if customer else "unknown"
    business = user.business_name if user else f"business {business_id}"

    print(
        f"\n[HANDOVER {urgency.upper()}]\n"
        f"Business : {business}\n"
        f"Customer : {phone}\n"
        f"Message  : {customer_message[:120]}\n"
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
