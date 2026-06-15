from sqlalchemy.orm import Session
from sqlalchemy import func  # Add this import
from app.models import Product, Conversation, Customer, MessageSender, User
from app.ai.provider import get_ai_response
from app.ai.prompt_builder import build_system_prompt
from app.ai import cache
from app.ai.token_utils import truncate_history_to_token_limit

SWAHILI_INDICATORS = {
        # greetings
        "habari", "mambo", "salama", "hujambo", "hamjambo",
        # commerce
        "ninataka", "nataka", "nunua", "kununua", "bei", "gharama",
        "lipa", "malipo", "mpesa", "order", "niorder", "bidhaa",
        "inapatikana", "stock", "tuma", "delivery", "ongea",
        # confirmations
        "ndiyo", "ndio", "hapana", "sawa", "sawa sawa", "asante",
        "karibu", "tafadhali", "samahani", "pole", "ngoja",
        # questions
        "nini", "wapi", "lini", "vipi", "kwa nini", "ngapi",
        # products / sizes
        "saizi", "rangi", "nyekundu", "nyeupe", "nyeusi", "kubwa", "ndogo",
        # pronouns / common words
        "mimi", "wewe", "yeye", "sisi", "wao", "tuna", "nina",
        "yake", "yangu", "yenu", "hii", "hiyo", "hizo",
    }


def get_business_prompt(user_id: int, db: Session) -> str:
    #Step 1 - check Redis first
    cached = cache.get_cached_business_prompt(user_id)
    if cached:
        print(f"[Cache HIT] Business { user_id} prompt from redis")
        return cached
    
    # Step 2 - cache miss, fetch from postgreSQL
    print(f"[Cache MISS] Fetching business { user_id} from PostgreSQL")
    
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"Business owner with id {user_id} not found")

    products = (
        db.query(Product)
        .filter(Product.user_id ==user_id)
        .filter(Product.is_available.is_(True))
        .all()
    )

    products_list = [
        {
            "name": p.name,
            "price": float(p.price),
            "is_available": p.is_available,
            "description": p.description
        }
        for p in products
    ]

    #Fetch knowledge base for the business
    knowledge_base =user.knowledge_base_text or ""
    business_type = getattr(user, "business_type", "retail") or "retail"

    prompt = build_system_prompt(
        business_name=user.business_name,
        products=products_list,
        knowledge_base=knowledge_base,
        business_type = business_type,
    )
    
    cache.cache_business_prompt(user_id,prompt)
    
    return prompt

def get_conversation_history(
    customer_id: int,
    user_id:int,
    db: Session,
    limit: int = 10
)-> list:
    
    # Step 1 — check Redis first
    cached = cache.get_cached_conversation(customer_id, user_id)
    if cached is not None:
        print("[Cache HIT] Conversation from Redis")
        return cached

    # Step 2 — cache miss, fetch from PostgreSQL
    print("[Cache MISS] Fetching conversation from PostgreSQL")
    

    messages = (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.user_id == user_id
        )
        .order_by(Conversation.timestamp.desc())
        .limit(limit)
        .all()
    )

    messages = list(reversed(messages))

    history = []
    for msg in messages:
            role = "user" if msg.sender.value == "customer" else "assistant"
            history.append({
                "role": role,
                "content": msg.message_text
        })
    while history and history[0]["role"] != "user":
        history.pop(0)
    #Step 3 - store in Redis for next time
    cache.cache_conversation(customer_id, user_id, history)

    return history

def save_message(
    customer_id: int,
    user_id:int,
    sender: str,
    message_text: str,
    language: str,
    db: Session
) -> None:
     
    # saves tp PostgreSQL permanently and updates Redis simultaneously
    new_message = Conversation(
        customer_id=customer_id,
        user_id=user_id,
        sender=MessageSender(sender),
        message_text=message_text,
        language=language
    )
    db.add(new_message)
    db.commit()
    
    # Update Redis cache immediately
    role = "user" if sender == "customer" else "assistant"
    cache.append_to_conversation_cache(
        customer_id=customer_id,
        user_id=user_id,
        message={"role": role, "content": message_text}
    )

def get_or_create_customer(phone_number: str, db: Session) -> Customer:
    #Finds a customer by phone number or creates them if first message.Phone number is the customer's only identity — no accounts needed.
    customer = (
        db.query(Customer)
        .filter(Customer.phone_number == phone_number)
        .first()
    )

    if not customer:
        customer = Customer(phone_number=phone_number)
        db.add(customer)
        db.commit()
        db.refresh(customer)
        print(f"[AISHA] New customer registered: {phone_number}")
    else:
        customer.last_seen = func.now()
        db.commit()

    return customer


def detect_handover(response: str) -> bool:
    return "[HANDOVER_REQUIRED]" in response

def classify_handover_urgency(customer_message: str) -> str:
    text_lower = customer_message.lower()
    if any(keyword in text_lower for keyword in URGENT_KEYWORDS):
        return "urgent"
    return "normal"

def clean_response(response: str) -> str:
    """
    Strips internal tags before sending response to customer.
    Customers must never see system tags in their WhatsApp chat.
    """
    return response.replace("[HANDOVER_REQUIRED]", "").strip()


def detect_language(text: str) -> str:
    text_lower = text.lower(). strip()
    words = set(text_lower.split())
    
    if words.intersection(SWAHILI_INDICATORS):
        return "sw"
    if any(indicator in text_lower for indicator in SWAHILI_INDICATORS):
        return "sw"
    return "en"


def process_customer_message(
    phone_number: str,
    message_text: str,
    user_id: int,
    db: Session
) -> dict:
    #Main orchestrator — called by the WhatsApp webhook on every incoming customer message.
    # 1. Find or create customer
    customer = get_or_create_customer(phone_number, db)

    # 2. Detect language for logging
    language = detect_language(message_text)

    # 3. Save customer message
    save_message(
        customer_id=customer.id,
        user_id=user_id,
        sender="customer",
        message_text=message_text,
        language=language,
        db=db
    )

    # 4. Build prompt from real database data
    system_prompt = get_business_prompt(user_id, db)

    # 5. Fetch conversation history from database
    history = get_conversation_history(customer.id, user_id, db)
    
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

    # 10. Clean internal tags from response
    clean = clean_response(clean)
    
    # 12. Classify handover urgency (used by dashboard prioritisation)
    urgency = classify_handover_urgency(message_text) if needs_handover else None

    # 11. Save AISHA's response
    save_message(
        customer_id=customer.id,
        user_id=user_id,
        sender="assistant",
        message_text=clean,
        language=detected_language,
        db=db
    )
    
    if needs_handover:
        notify_handover(customer.id, user_id, message_text, urgency, db)

    return {
        "response": clean,
        "needs_handover": needs_handover,
        "handover_urgency": urgency,
        "customer_id": customer.id,
        "language": language,
        "response_language": detected_language
    }
    
def notify_handover(
    customer_id: int,
    user_id: int,
    customer_message: str,
    urgency: str,
    db: Session
) -> None:
    """
    Alerts the business owner when AISHA triggers a handover.
    Logs to console AND sends a WhatsApp alert to the owner's number.
    """
    from app.whatsapp.client import send_owner_alert  # local import avoids circular

    user     = db.query(User).filter(User.id == user_id).first()
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    phone    = customer.phone_number if customer else "unknown"
    business = user.business_name   if user     else f"business {user_id}"
    owner_phone = getattr(user, "whatsapp_phone_number", None)

    print(
        f"\n[HANDOVER {urgency.upper()}]\n"
        f"Business : {business}\n"
        f"Customer : {phone}\n"
        f"Message  : {customer_message[:120]}\n"
        f"Owner    : {owner_phone or 'not configured'}\n"
    )

    # Send WhatsApp alert if owner has a number configured
    if owner_phone:
        sent = send_owner_alert(
            owner_phone=owner_phone,
            customer_phone=phone,
            customer_message=customer_message,
            urgency=urgency,
        )
        if not sent:
            print(f"[Handover] Failed to send WhatsApp alert to owner {owner_phone}")
    else:
        print("[Handover] Owner has no whatsapp_phone_number — alert skipped")
    
    
    
def parse_ai_response(raw_response:str) -> tuple:
    """
    Parses the AI's self-tagged response into language and clean text.Parses the AI's self-tagged response into language and clean text.
    """
    if not raw_response:
        return "en", ""
    
    lines = raw_response.strip().split("\n", 1)
    first_line = lines[0].strip()
    
    #Happy path -AI included the language tag correctly
    if first_line == "[LANG:en]":
        clean = lines[1].strip() if len(lines) > 1 else ""
        return "en", clean
    
    if first_line == "[LANG:sw]":
        clean = lines[1].strip() if len(lines) > 1 else ""
        return "sw", clean
    
     # Fallback — AI forgot the tag (happens occasionally)
    # Use simple word check rather than a library
    print("AISHA WARNING] AI response missing language tag — using word fallback")
    language = detect_language(raw_response)
    return language, raw_response.strip()

# Handover
URGENT_KEYWORDS = {
    #English
    "complaint", "refund", "scam", "fraud", "angry", "terrible",
    "wrong","broken", "missing" , "stolen" , "cheat" , "lied",
    #Kiswahili
    "malalamiko", "rudisha pesa", "uongo", "hasira", "mbaya sana",
    "ilinibidi", "nilidanganywa", "tatizo kubwa",
}
    

    
    



    