from app.ai.provider import get_ai_response
from app.ai.prompt_builder import build_system_prompt

# Fake business data to test with
business_name = "Zawadi Boutique"

products = [
    {
        "name": "Nike Air Force 1",
        "price": 4500,
        "is_available": True,
        "description": "Available in sizes 6-11, red and white",
    },
    {
        "name": "Adidas Samba",
        "price": 5200,
        "is_available": True,
        "description": "Classic white, sizes 6-11",
    },
]

knowledge_base = """
Business hours: Monday to Saturday, 8am to 8pm
Location: Westlands, Nairobi — next to Sarit Centre
Delivery: Available within Nairobi for KSh 200
Payment: M-Pesa to 0712 345 678 (Zawadi Boutique)
Returns: Within 7 days with receipt
"""

# Build the system prompt
system_prompt = build_system_prompt(business_name, products, knowledge_base)

# Simulate a conversation
conversation_history = [{"role": "user", "content": "Habari, mna sneakers nyekundu?"}]

print("Testing AISHA AI...\n")
print("=" * 50)

# Test 1 — English
print("TEST 1: English customer")
print("-" * 30)
history_en = [{"role": "user", "content": "Hi, what sneakers do you have?"}]
print("Customer:", history_en[-1]["content"])
response1 = get_ai_response(system_prompt, history_en)
print("AISHA:", response1)

print()

# Test 2 — Kiswahili
print("TEST 2: Kiswahili customer")
print("-" * 30)
history_sw = [{"role": "user", "content": "Habari, mna sneakers nyekundu?"}]
print("Customer:", history_sw[-1]["content"])
response2 = get_ai_response(system_prompt, history_sw)
print("AISHA:", response2)

print()

# Test 3 — Multi-turn conversation in English
print("TEST 3: Multi-turn English conversation")
print("-" * 30)
history_multi = [
    {"role": "user", "content": "What sneakers do you have?"},
    {"role": "assistant", "content": response1},
    {"role": "user", "content": "How much is the Nike Air Force 1?"},
]
print("Customer:", history_multi[-1]["content"])
response3 = get_ai_response(system_prompt, history_multi)
print("AISHA:", response3)

print()

# Test 4 — Order flow in Kiswahili
print("TEST 4: Customer wants to order in Kiswahili")
print("-" * 30)
history_order = [
    {"role": "user", "content": "Habari, mna sneakers nyekundu?"},
    {"role": "assistant", "content": response2},
    {"role": "user", "content": "Ninataka kuorder Nike nyekundu size 8"},
]
print("Customer:", history_order[-1]["content"])
response4 = get_ai_response(system_prompt, history_order)
print("AISHA:", response4)

print()
print("=" * 50)
print("All tests complete.")
