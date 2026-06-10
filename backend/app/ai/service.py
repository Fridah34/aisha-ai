from sqlalchemy.orm import Session
from sqlalchemy import func  # Add this import
from app.models import Product, Conversation, Customer, MessageSender, User
from app.ai.provider import get_ai_response
from app.ai.prompt_builder import build_system_prompt
from app.ai import cache

def get_business_prompt(user_id: int, db: Session) -> str:
    #Step 1 - check Redis first
    cached = cache.get_cached_business_prompt(user_id)
    if cached:
        print(f"Cache HIT-business { user_id} prompt from redis")
        return cached
    
    # Step 2 - cache miss, fetch from postgreSQL
    print(f"Cache MISS- fetching business { user_id} from PostgreSQL")
    
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"Business owner with id {user_id} not found")

    products = (
        db.query(Product)
        .filter(Product.user_id ==user_id)
        .filter(Product.is_available == True)
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

    prompt = build_system_prompt(
        business_name=user.business_name,
        products=products_list,
        knowledge_base=knowledge_base
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
        print(f"Cache HIT — conversation from Redis")
        return cached

    # Step 2 — cache miss, fetch from PostgreSQL
    print(f"Cache MISS — fetching conversation from PostgreSQL")
    

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
        print(f"New customer registered: {phone_number}")
    else:
        customer.last_seen = func.now()
        db.commit()

    return customer


def detect_handover(response: str) -> bool:
    return "[HANDOVER_REQUIRED]" in response


def clean_response(response: str) -> str:
    """
    Strips internal tags before sending response to customer.
    Customers must never see system tags in their WhatsApp chat.
    """
    return response.replace("[HANDOVER_REQUIRED]", "").strip()


def detect_language(text: str) -> str:
    #Simple language detection for database logging.The AI handles actual language matching in responses
    swahili_words = [
        "habari", "ninataka", "tuna", "bei", "nini",
        "je", "sawa", "asante", "karibu", "ngoja"
    ]
    text_lower = text.lower()
    if any(word in text_lower for word in swahili_words):
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

    # 6. Ensure current message is at the end of history
    if not history or history[-1]["content"] != message_text:
        history.append({"role": "user", "content": message_text})

    # 7. Get AI response
    raw_response = get_ai_response(system_prompt, history)

    # 8. Check for handover trigger
    needs_handover = detect_handover(raw_response)

    # 9. Clean internal tags from response
    clean = clean_response(raw_response)

    # 10. Detect response language for logging
    response_language = detect_language(clean)

    # 11. Save AISHA's response
    save_message(
        customer_id=customer.id,
        user_id=user_id,
        sender="assistant",
        message_text=clean,
        language=response_language,
        db=db
    )

    return {
        "response": clean,
        "needs_handover": needs_handover,
        "customer_id": customer.id,
        "language": language
    }
    



    