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

# 🔐 API KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🧠 simple analytics
analytics_data = {}

# 📩 request model
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    history: list = []


# 🧠 prompt builder
def build_prompt(subject, question, history):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain step-by-step in simple language.

If not study related, reply:
"Ye chacha tula samajhta ka nahi 😤 Ja jaaun abhyas kar 📚🔥"
"""

    teachers = {
        "physics": "Avinash 2.0 Physics teacher",
        "maths": "Dharmentra 2.0 Maths teacher",
        "chemistry": "Abhishek 2.0 Chemistry teacher",
        "biology": "Ashutosh 2.0 Biology teacher"
    }

    teacher = teachers.get(subject, "Teacher")

    history_text = ""
    for h in history[-5:]:
        history_text += f"{h['role']}: {h['text']}\n"

    return f"{rules}\nYou are {teacher}\n\n{history_text}\nQuestion: {question}"


# 🤖 TEXT
def ask_text(prompt):

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, params=params, json=payload)
        data = res.json()

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in data:
            return data["error"]["message"]

        else:
            return "⚠️ No AI response"

    except Exception as e:
        return f"⚠️ {str(e)}"


# 🤖 IMAGE
def ask_image(prompt, img):

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
                            "data": img
                        }
                    }
                ]
            }
        ]
    }

    try:
        res = requests.post(url, params=params, json=payload)
        data = res.json()

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in data:
            return data["error"]["message"]

        else:
            return "⚠️ Image AI failed"

    except Exception as e:
        return f"⚠️ {str(e)}"


# 🚀 MAIN CHAT
@app.post("/chat")
def chat(msg: Message):

    prompt = build_prompt(msg.subject, msg.message, msg.history)

    if msg.image:
        reply = ask_image(prompt, msg.image)
    else:
        reply = ask_text(prompt)

    # simple analytics (global)
    analytics_data[msg.subject] = analytics_data.get(msg.subject, 0) + 1

    return {"reply": reply}


# 📊 analytics
@app.get("/analytics")
def analytics():
    return {"data": analytics_data}


# 📅 study plan
@app.get("/study-plan")
def study_plan():
    return {
        "plan": "Study Physics, Chemistry, Maths/Biology daily. Revise weekly."
    }


# 🏠 home
@app.get("/")
def home():
    return {"message": "E Acad Running 🚀"}
