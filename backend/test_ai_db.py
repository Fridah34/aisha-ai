from app import models
from app.ai.service import process_customer_message
from app.database import SessionLocal, engine

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # First create a test business owner in the database
    # Check if test user already exists
    test_user = (
        db.query(models.User).filter(models.User.email == "test@zawadi.com").first()
    )

    if not test_user:
        test_user = models.User(
            name="Test Owner",
            email="test@zawadi.com",
            business_name="Zawadi Boutique",
            hashed_password="hashed_placeholder",
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"Created test business: {test_user.business_name}")

    # Add test products if none exist
    existing_products = (
        db.query(models.Product)
        .filter(models.Product.business_id == test_user.id)
        .count()
    )

    if existing_products == 0:
        products = [
            models.Product(
                business_id=test_user.id,
                name="Nike Air Force 1",
                description="Available in red and white, sizes 6-11",
                price=4500,
                is_available=True,
            ),
            models.Product(
                business_id=test_user.id,
                name="Adidas Samba",
                description="Classic white, sizes 6-11",
                price=5200,
                is_available=True,
            ),
            models.Product(
                business_id=test_user.id,
                name="Puma Suede Classic",
                description="Black, sizes 6-11",
                price=3800,
                is_available=True,
            ),
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
        message_text="Good morning. I am looking for Nike sneakers. What sizes and colors do you have available?",
        business_id=test_user.id,
        db=db,
    )
    print(
        "Customer: Good morning. I am looking for Nike sneakers. What sizes and colors do you have available?"
    )
    print("AISHA:", result1["response"])
    print("Response language:", result1["response_language"])

    # Test 2 — Pure Kiswahili customer
    print("\nTEST 2: Kiswahili customer")
    result2 = process_customer_message(
        phone_number="+254722222222",
        message_text="Habari, ninataka kujua bei za sneakers zenu zote",
        business_id=test_user.id,
        db=db,
    )
    print("Customer: Habari, ninataka kujua bei za sneakers zenu zote")
    print("AISHA:", result2["response"])
    print("Response language:", result2["response_language"])

    # Test 3 — Mixed language (Sheng)
    print("\nTEST 3: Mixed language customer")
    result3 = process_customer_message(
        phone_number="+254733333333",
        message_text="Ninataka red Nike size 8, bei yake ni how much?",
        business_id=test_user.id,
        db=db,
    )
    print("Customer: Ninataka red Nike size 8, bei yake ni how much?")
    print("AISHA:", result3["response"])
    print("Response language:", result3["response_language"])

    # Test 4 — English order flow
    print("\nTEST 4: English customer placing order")
    result4 = process_customer_message(
        phone_number="+254712345678",
        message_text="I would like to order the Nike Air Force 1 in size 9 please",
        business_id=test_user.id,
        db=db,
    )
    print("Customer: I would like to order the Nike Air Force 1 in size 9 please")
    print("AISHA:", result4["response"])
    print("Response language:", result4["response_language"])

    # Test 5 — English handover trigger
    print("\nTEST 5: English handover")
    result5 = process_customer_message(
        phone_number="+254744444444",
        message_text="Do you offer corporate bulk purchasing agreements?",
        business_id=test_user.id,
        db=db,
    )
    print("Customer: Do you offer corporate bulk purchasing agreements?")
    print("AISHA:", result5["response"])
    print("Needs handover:", result5["needs_handover"])
    print("Response language:", result5["response_language"])

    print("\n" + "=" * 50)
    print("All tests complete")

    # Show what got saved
    total_messages = (
        db.query(models.Conversation)
        .filter(models.Conversation.business_id == test_user.id)
        .count()
    )
    total_customers = db.query(models.Customer).count()
    print(f"Messages saved to database: {total_messages}")
    print(f"Customers in database: {total_customers}")

finally:
    db.close()
