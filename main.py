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

# 📊 Memory
student_memory = {}

class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"


# 🧠 Prompt builder
def build_prompt(subject, question, weak_topics):
    return f"""
You are an expert teacher for Class 8–12, JEE, NEET.

Weak topics: {weak_topics}

Answer in format:
1. Concept
2. Formula
3. Step-by-step solution
4. Final answer

Use LaTeX where needed.

Question: {question}
"""


# 🤖 AI
def ask_ai(prompt, image=None):

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
        "contents": [
            {
                "parts": parts
            }
        ]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    if "candidates" in result:
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except:
            return "⚠️ Error reading AI response"

    elif "error" in result:
        return f"⚠️ Gemini Error: {result['error']['message']}"

    else:
        return "⚠️ Unexpected AI response"


# 🚀 Chat API
@app.post("/chat")
def chat(msg: Message):

    user = msg.user_id

    if user not in student_memory:
        student_memory[user] = {}

    text = msg.message.lower()

    topic = "General"

    if "force" in text or "motion" in text:
        topic = "Mechanics"
    elif "current" in text or "electric" in text:
        topic = "Electricity"
    elif "atom" in text or "mole" in text:
        topic = "Chemistry"
    elif "cell" in text or "plant" in text:
        topic = "Biology"

    student_memory[user][topic] = student_memory[user].get(topic, 0) + 1

    weak_topics = sorted(student_memory[user], key=student_memory[user].get, reverse=True)

    prompt = build_prompt(msg.subject, msg.message, weak_topics)

    reply = ask_ai(prompt, msg.image)

    return {"reply": reply}


# 📊 Analytics
@app.get("/analytics/{user_id}")
def analytics(user_id: str):
    return {"data": student_memory.get(user_id, {})}


# 📅 Study Planner
@app.get("/study-plan/{user_id}")
def study_plan(user_id: str):

    if user_id not in student_memory:
        return {"plan": "No data available yet. Ask some doubts first."}

    weak_topics = sorted(student_memory[user_id], key=student_memory[user_id].get, reverse=True)

    prompt = f"""
Create a 3-day study plan for a JEE/NEET student.

Weak topics: {weak_topics}

Format:

Day 1:
- Topic
- Practice
- Revision

Day 2:
...

Day 3:
...
"""

    plan = ask_ai(prompt)

    return {"plan": plan}


@app.get("/")
def home():
    return {"message": "E Acad AI Running 🚀"}
