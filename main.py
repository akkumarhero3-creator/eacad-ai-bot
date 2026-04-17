from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS (for Wix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Gemini API key from Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🧠 Simple in-memory storage
student_analytics = {}

# 📩 Request model
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    history: list = []
    user: str = "guest"


# 🧠 Prompt Builder
def build_prompt(subject, question, history):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain answers step-by-step in simple language.

If NOT study-related, reply EXACTLY:
"Ye chacha tula samajhta ka nahi 😤 Ja jaaun abhyas kar 📚🔥"
"""

    teacher_map = {
        "physics": "Avinash 2.0 (Physics expert)",
        "maths": "Dharmentra 2.0 (Maths expert)",
        "chemistry": "Abhishek 2.0 (Chemistry expert)",
        "biology": "Ashutosh 2.0 (Biology expert)"
    }

    teacher = teacher_map.get(subject, "Teacher")

    # 🧠 Add memory (last 5 messages)
    history_text = ""
    for h in history[-5:]:
        history_text += f"{h['role']}: {h['text']}\n"

    return f"{rules}\nYou are {teacher}\n\nConversation:\n{history_text}\nQuestion: {question}"


# 🤖 TEXT AI
def ask_text(prompt):

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, params=params, json=payload)
        data = res.json()

        print("TEXT DEBUG:", data)

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in data:
            return f"⚠️ Gemini Error: {data['error']['message']}"

        else:
            return "⚠️ AI returned empty response"

    except Exception as e:
        return f"⚠️ Exception: {str(e)}"


# 🤖 IMAGE AI
def ask_image(prompt, base64_img):

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_img
                        }
                    }
                ]
            }
        ]
    }

    try:
        res = requests.post(url, params=params, json=payload)
        data = res.json()

        print("IMAGE DEBUG:", data)

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in data:
            return f"⚠️ Gemini Error: {data['error']['message']}"

        else:
            return "⚠️ Image AI returned empty response"

    except Exception as e:
        return f"⚠️ Exception: {str(e)}"


# 🚀 MAIN CHAT API
@app.post("/chat")
def chat(msg: Message):

    prompt = build_prompt(msg.subject, msg.message, msg.history)

    # 📸 If image exists
    if msg.image:
        reply = ask_image(prompt, msg.image)
    else:
        reply = ask_text(prompt)

    # 📊 Analytics per user
    user = msg.user

    student_analytics.setdefault(user, {})
    student_analytics[user][msg.subject] = student_analytics[user].get(msg.subject, 0) + 1

    return {"reply": reply}


# 📊 ANALYTICS API
@app.get("/analytics/{student}")
def analytics(student: str):

    data = student_analytics.get(student, {
        "physics": 0,
        "maths": 0,
        "chemistry": 0,
        "biology": 0
    })

    return {"data": data}


# 📅 STUDY PLAN API
@app.get("/study-plan/{student}")
def study_plan(student: str):

    plan = """
📅 Weekly Study Plan:

Day 1: Physics - Laws of Motion  
Day 2: Chemistry - Mole Concept  
Day 3: Maths - Functions  
Day 4: Biology - Cell  
Day 5: Revision  
Day 6: Practice Questions  
Day 7: Mock Test  
"""

    return {"plan": plan}


# 🏠 HOME
@app.get("/")
def home():
    return {"message": "E Acad AI Backend Running 🚀"}
