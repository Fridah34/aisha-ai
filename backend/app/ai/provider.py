import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

#function calling for the AI-same way and get a string back
def get_ai_response(prompt:str,conversation_history: list= []) -> str:
    if conversation_history is None:
        conversation_history = []
    try:
        if AI_PROVIDER == "claude":
            return _call_claude(prompt, conversation_history)
        elif AI_PROVIDER == "gemini":
            return _call_gemini(prompt,conversation_history)
        elif AI_PROVIDER == "groq" :
            return _call_groq(prompt,conversation_history)
        else:
            raise ValueError(f"Unknown AI provider: {AI_PROVIDER}")

    except Exception as primary_error:
        # If primary provider fails, automatically fall back to Groq
        # This keeps AISHA running even if Gemini has an outage
        print(f"Primary AI provider failed: {primary_error}")
        
        if AI_PROVIDER != "groq":
            print("Falling back to Groq...")
            try:
                return _call_groq(prompt,conversation_history)
            except Exception as fallback_error:
                print(f"Groq fallback also failed: {fallback_error}")

        return (
            "Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye."
            "Sorry, we are experiencing a brief issue. Please try again shortly."
        )

def _call_gemini(prompt: str, conversation_history: list) -> str:
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=prompt
    )

    # Convert history — all messages except the last one
    gemini_history = []
    for message in conversation_history[:-1]:
        role = "model" if message["role"] == "assistant" else "user"
        gemini_history.append({
            "role": role,
            "parts": [message["content"]]
        })

    chat = model.start_chat(history=gemini_history)

    last_message = conversation_history[-1]["content"] if conversation_history else "Hello"
    response = chat.send_message(last_message)
    return response.text


def _call_claude(prompt: str, conversation_history: list) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=prompt,
        messages=conversation_history
    )

    return response.content[0].text


def _call_groq(prompt: str, conversation_history: list) -> str:
    """
    Groq runs Llama 3 — completely free, no credit card needed.
    Fastest response times of all three providers.
    Great Claude alternative for development and demos.
    """
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Groq uses the same message format as Claude/OpenAI
    # so no conversion needed — just prepend the system prompt
    messages = [{"role": "system", "content": prompt}] + conversation_history

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # best free model on Groq
        messages=messages,
        max_tokens=1024,
        temperature=0.7
    )

    return response.choices[0].message.content


