from app.ai.language import detect_language, get_language_name

test_messages = [
    # Clear Swahili
    ("Habari, mna sneakers nyekundu?", "sw"),
    ("Ninataka kuorder Nike size 8", "sw"),
    ("Bei yake ni ngapi?", "sw"),
    ("Asante sana", "sw"),
    ("Sawa", "sw"),

    # Clear English
    ("Hi, what shoes do you have?", "en"),
    ("How much is the Nike Air Force 1?", "en"),
    ("I want to place an order", "en"),
    ("Ok", "en"),

    # Short messages — hardest to detect
    ("Bei?", "sw"),
    ("Nini?", "sw"),
    ("Yes", "en"),

    # Sheng / mixed
    ("Ninataka red sneakers size 8", "sw"),
    ("Hi, nataka order moja", "sw"),
]

print("Language Detection Tests")
print("=" * 50)

passed = 0
failed = 0

for message, expected in test_messages:
    result = detect_language(message)
    status = "right" if result == expected else "wrong"
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f"{status} '{message}'")
    print(f"   Expected: {get_language_name(expected)} | Got: {get_language_name(result)}")

print()
print(f"Results: {passed} passed, {failed} failed out of {len(test_messages)} tests")