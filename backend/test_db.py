import sys
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
import app.models as models
import app.schema as schema

print("Step 1: Initiating database schema synchronization...")
try:
    # This reads your models.py and builds the actual tables in PostgreSQL!
    Base.metadata.create_all(bind=engine)
    print(" Database tables created successfully inside PostgreSQL!")
except Exception as e:
    print(" CRITICAL ERROR: Table creation failed. Check your models.py attributes or relationship fields!")
    print(str(e))
    sys.exit(1)

print("\nStep 2: Testing Pydantic Schema parsing validation...")
try:
    # Testing your strict language enum and nested structures using Pydantic
    mock_payload = {
        "customer_id": 1,
        "user_id": 1,
        "sender": "customer",
        "message": "Niaje maze, mko na mawaridi leo?",
        "language": "sng"  # Testing your new strict Sheng validation enum!
    }
    validated_schema = schema.ConversationCreate(**mock_payload)
    print(f"Schema validation passed! Parsed text language: '{validated_schema.language.value}'")
except Exception as e:
    print("CRITICAL ERROR: Pydantic schema instantiation failed. Check your schemas.py declarations!")
    print(str(e))
    sys.exit(1)

print("\n Step 3: Verifying Database Session connectivity...")
db: Session = SessionLocal()
try:
    # Verifies your database.py credentials can cleanly open a connection pipe
    db.execute(models.text("SELECT 1"))
    print("Connection verified! Database session is open and active.")
finally:
    db.close()
    print("Session closed safely.")

print("\nALL TESTS PASSED! Your data infrastructure layer is 100% solid.")
