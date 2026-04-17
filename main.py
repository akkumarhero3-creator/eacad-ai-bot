from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

student_memory = {}

class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"


# 🔥 HINGLISH + FUN PROMPT
def build_prompt(subject, question, weak_topics):
    return f"""
You are a top JEE/NEET teacher.

Speak in Hinglish (Hindi + English mix).
Be friendly, energetic and slightly funny 😄

Style:
- Use phrases like "arre bhai", "samjha kya?", "easy hai"
- Keep tone motivating
- Don't overdo jokes

Format STRICTLY:

### Concept
Explain simply

### Formula
Use proper equations

### Step-by-step
Teach like real teacher

### Final Answer
Short crisp answer

If question is outside syllabus:
Say:
"Arre bhai 😄 yaha sirf padhai hoti hai, ja padhai kar!"

Question: {question}
"""


# 🤖 AI FUNCTION
def ask_ai(prompt, image=None):

    if not GEMINI_API_KEY:
        return "⚠️ API key missing"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    parts = [{"text": prompt}]

    if image:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image
            }
        })

    payload = {
        "contents": [{"parts": parts}]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()

        print(result)

        if "candidates" in result:
            return result["candidates"][0]["content"]["parts"][0]["text"]

        if "error" in result:
            return f"⚠️ Gemini Error: {result['error']['message']}"

        return "⚠️ No AI response"

    except Exception as e:
        return f"⚠️ Server Error: {str(e)}"


# 🚀 CHAT
@app.post("/chat")
def chat(msg: Message):

    user = msg.user_id

    if user not in student_memory:
        student_memory[user] = {}

    text = msg.message.lower()

    topic = "General"

    if "force" in text or "motion" in text:
        topic = "Mechanics"
    elif "current" in text:
        topic = "Electricity"
    elif "atom" in text:
        topic = "Chemistry"
    elif "cell" in text:
        topic = "Biology"

    student_memory[user][topic] = student_memory[user].get(topic, 0) + 1

    weak_topics = sorted(student_memory[user], key=student_memory[user].get, reverse=True)

    prompt = build_prompt(msg.subject, msg.message, weak_topics)

    reply = ask_ai(prompt, msg.image)

    return {"reply": reply}


# 📊 ANALYTICS
@app.get("/analytics/{user_id}")
def analytics(user_id: str):
    return {"data": student_memory.get(user_id, {})}


# 📅 STUDY PLAN
@app.get("/study-plan/{user_id}")
def study_plan(user_id: str):

    if user_id not in student_memory:
        return {"plan": "Pehle thoda padh le 😄"}

    weak_topics = list(student_memory[user_id].keys())

    prompt = f"""
Create a 3-day Hinglish study plan.

Weak topics: {weak_topics}
"""

    plan = ask_ai(prompt)

    return {"plan": plan}


@app.get("/")
def home():
    return {"message": "E Acad Running 🚀"}
