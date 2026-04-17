from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS (important for Wix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 📊 Student analytics memory
student_memory = {}

class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"


# 🧠 Prompt
def build_prompt(subject, question, weak_topics):
    return f"""
You are an expert teacher for Class 8–12, JEE, NEET.

Weak topics: {weak_topics}

Answer in format:
1. Concept
2. Formula
3. Step-by-step solution
4. Final answer

Use simple language.
Use LaTeX for equations like \\(F=ma\\)

Question: {question}
"""


# 🤖 Gemini API
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
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return str(result)


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


# 📊 Analytics API
@app.get("/analytics/{user_id}")
def analytics(user_id: str):
    return {"data": student_memory.get(user_id, {})}


# 🏠 Home
@app.get("/")
def home():
    return {"message": "E Acad AI Running 🚀"}
