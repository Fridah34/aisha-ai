from app.database import SessionLocal
from app.ai.service import process_customer_message
from app import models
from app.database import engine

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # First create a test business owner in the database
    # Check if test user already exists
    test_user = db.query(models.User).filter(
        models.User.email == "test@zawadi.com"
    ).first()

    if not test_user:
        test_user = models.User(
            name="Test Owner",
            email="test@zawadi.com",
            business_name="Zawadi Boutique",
            hashed_password="hashed_placeholder"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"Created test business: {test_user.business_name}")

    # Add test products if none exist
    existing_products = db.query(models.Product).filter(
        models.Product.user_id == test_user.id
    ).count()

    if existing_products == 0:
        products = [
            models.Product(
                user_id=test_user.id,
                name="Nike Air Force 1",
                description="Available in red and white, sizes 6-11",
                price=4500,
                is_available=True
            ),
            models.Product(
                user_id=test_user.id,
                name="Adidas Samba",
                description="Classic white, sizes 6-11",
                price=5200,
                is_available=True
            ),
            models.Product(
                user_id=test_user.id,
                name="Puma Suede Classic",
                description="Black, sizes 6-11",
                price=3800,
                is_available=True
            )
        ]
        db.add_all(products)
        db.commit()
        print(f"Added {len(products)} test products")

    print("\nTesting with REAL database data...")
    print("=" * 50)

    # Test 1 — English customer
    print("\nTEST 1: English customer (first message)")
    result1 = process_customer_message(
        phone_number="+254712345678",
        message_text="Hi, what shoes do you have?",
        user_id=test_user.id,
        db=db
    )
    print("Customer: Hi, what shoes do you have?")
    print("AISHA:", result1["response"])
    print("Language detected:", result1["language"])
    print("Needs handover:", result1["needs_handover"])

    # Test 2 — Same customer, Kiswahili, second message
    print("\nTEST 2: Same customer continues in Kiswahili")
    result2 = process_customer_message(
        phone_number="+254712345678",
        message_text="Ninataka kuorder Nike nyekundu size 8",
        user_id=test_user.id,
        db=db
    )
    print("Customer: Ninataka kuorder Nike nyekundu size 8")
    print("AISHA:", result2["response"])

    # Test 3 — New customer, question AISHA can't answer
    print("\nTEST 3: Question requiring handover")
    result3 = process_customer_message(
        phone_number="+254798765432",
        message_text="Can I get a bulk discount for 50 pairs?",
        user_id=test_user.id,
        db=db
    )
    print("Customer: Can I get a bulk discount for 50 pairs?")
    print("AISHA:", result3["response"])
    print("Needs handover:", result3["needs_handover"])

    print("\n" + "=" * 50)
    print("Database test complete.")

    # Show what got saved
    total_messages = db.query(models.Conversation).filter(
        models.Conversation.user_id == test_user.id
    ).count()
    total_customers = db.query(models.Customer).count()
    print(f"Messages saved to database: {total_messages}")
    print(f"Customers in database: {total_customers}")

finally:
    db.close()