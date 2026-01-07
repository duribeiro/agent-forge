
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

def check_api_key():
    return api_key is not None

def upload_to_gemini(path, mime_type=None):
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        return file
    except Exception as e:
        raise Exception(f"Upload failed: {e}")

def wait_for_process(file):
    while True:
        file = genai.get_file(file.name)
        if file.state.name == "PROCESSING":
            time.sleep(2)
        elif file.state.name == "ACTIVE":
            return file
        elif file.state.name == "FAILED":
            raise Exception("Google failed to process the video.")
        else:
            time.sleep(2)

def get_best_model():
    candidates = ["gemini-2.0-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-flash"]
    try:
        available = [m.name.replace("models/", "") for m in genai.list_models()]
        for c in candidates:
            if c in available: return c
        return "gemini-1.5-flash"
    except:
        return "gemini-1.5-flash"

def generate_agent_assets(video_path, agent_goal):
    video_file = upload_to_gemini(video_path, mime_type="video/mp4")
    ready_file = wait_for_process(video_file)
    
    model_name = get_best_model()
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={"temperature": 0.4, "max_output_tokens": 8192}
    )

    kb_prompt = """
    ROLE: Senior Knowledge Engineer.
    TASK: Extract valid, structured knowledge from this video to train a LLM Agent.
    
    INSTRUCTIONS:
    1. Transcribe the core content (Audio).
    2. OCR: Read all visual slides/text on screen.
    3. Structure: Use strictly Markdown (H1, H2, Bullets).
    4. NO Fluff: Remove "hello", "subscribe", etc. Only raw knowledge.
    
    OUTPUT: Markdown.
    """
    
    kb_response = model.generate_content([ready_file, kb_prompt])
    knowledge_base = kb_response.text

    persona_prompt = f"""
    ROLE: Expert Prompt Engineer.
    CONTEXT: One video about "{agent_goal}".
    
    TASK: Write a SYSTEM PROMPT that defines an AI Agent based on the knowledge provided below.
    
    AGENT GOAL: {agent_goal}
    
    INSTRUCTIONS FOR PROMPT GENERATION:
    - Define a Persona (Name, Tone, Style).
    - Define Rules (What to answer, what to ignore).
    - Define Format (How to structure answers).
    - The prompt must be ready to paste into OpenAI/Claude/Gemini.
    
    KNOWLEDGE BASE CONTEXT:
    {knowledge_base[:30000]} 
    """
    
    sys_response = model.generate_content(persona_prompt)
    system_prompt = sys_response.text
    
    return knowledge_base, system_prompt

def get_chat_response(messages, system_prompt, knowledge_base):
    """
    Interactive Chat Logic for 'Test Agent'
    """
    model_name = get_best_model() # Reuse the fast/cheap model
    
    # We construct a chat session with the System Instruction
    # Note: Gemini python lib uses 'system_instruction' arg in GenerativeModel
    
    full_instruction = f"""
    {system_prompt}
    
    ---
    KNOWLEDGE BASE:
    {knowledge_base}
    """
    
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=full_instruction
    )
    
    # Convert session messages to Gemini format
    # Streamlit uses {"role": "user", "content": "..."}
    # Gemini uses [{"role": "user", "parts": ["..."]}]
    history = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    chat = model.start_chat(history=history)
    
    # We assume the last message is already in history? 
    # Actually start_chat takes history *before* the new message.
    # So we pop the last one to send it? 
    
    if not messages: return "Olá! Sou seu agente."
    
    last_msg = messages[-1]["content"]
    # We need to exclude the last message from history passed to start_chat 
    # Otherwise we might duplicate or confuse logic if we send it via send_message
    
    # Let's clean up:
    history_minus_last = history[:-1] if len(history) > 0 else []
    
    chat = model.start_chat(history=history_minus_last)
    response = chat.send_message(last_msg)
    
    return response.text
