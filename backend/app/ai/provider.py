import os
from dotenv import load_dotenv

load_dotenv()
# Cost tracking - switch to Groq when Gemini credit 
GEMINI_CREDIT_THRESHOLD = float(os.getenv("GEMINI_CREDIT_THRESHOLD", "10.0"))

#function calling for the AI-same way and get a string back
def get_ai_response(prompt:str,conversation_history: list= None) -> str:
    if conversation_history is None:
        conversation_history = []
        
    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()
    
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
        print(f"[ AISHA ] Primary AI provider '{AI_PROVIDER}'failed: {primary_error}")
        
        if AI_PROVIDER != "groq":
            print("Falling back to Groq...")
            try:
                return _call_groq(prompt,conversation_history)
            except Exception as fallback_error:
                print(f"[AISHA]Groq fallback also failed: {fallback_error}")

        return (
            "Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye."
            "Sorry, we are experiencing a brief issue. Please try again shortly."
        )

def _call_gemini(prompt: str, conversation_history: list) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Context, Part
    
     # Initialize Vertex AI with your project
    vertexai.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0949791582"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )

    model = GenerativeModel(
        model_name="gemini-2.0-flash-001",
        system_instruction=prompt,
    )
    
    #Guard - if history is empty, send a default greeting
    if not conversation_history:
        response = model.generate_content("Hello")
        return response.text

    # Convert history — all messages except the last one
    
    history = []
    for msg in conversation_history[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append(
            Content(
                role=role,
                parts=[Part.from_text(msg["content"])])
            )
        
    chat = model.start_chat(history=history)
    
    #send the latest message
    last_message = conversation_history[-1]["content"]
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


