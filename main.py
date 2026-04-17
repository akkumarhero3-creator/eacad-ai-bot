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

# 🔐 API KEY (Render)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🧠 Analytics (simple)
analytics_data = {}

# 📩 Request model
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    history: list = []


# 🧠 PROMPT BUILDER
def build_prompt(subject, question, history):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain step-by-step in simple language.

If NOT study-related, reply EXACTLY:
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


# 🤖 UNIVERSAL AI CALL (AUTO MODEL FIX)
def call_gemini(payload):

    models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]

    for model in models:

        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
        params = {"key": GEMINI_API_KEY}

        try:
            res = requests.post(url, params=params, json=payload)
            data = res.json()

            print(f"TRYING MODEL: {model}", data)

            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]

            elif "error" in data:
                continue  # try next model

        except:
            continue

    return "⚠️ All AI models failed. Check API key."


# 🤖 TEXT
def ask_text(prompt):

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    return call_gemini(payload)


# 🤖 IMAGE
def ask_image(prompt, img):

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

    return call_gemini(payload)


# 🚀 MAIN CHAT
@app.post("/chat")
def chat(msg: Message):

    prompt = build_prompt(msg.subject, msg.message, msg.history)

    if msg.image:
        reply = ask_image(prompt, msg.image)
    else:
        reply = ask_text(prompt)

    # 📊 Analytics
    analytics_data[msg.subject] = analytics_data.get(msg.subject, 0) + 1

    return {"reply": reply}


# 📊 ANALYTICS
@app.get("/analytics")
def analytics():
    return {"data": analytics_data}


# 📅 STUDY PLAN
@app.get("/study-plan")
def study_plan():
    return {
        "plan": "Study daily: Physics, Chemistry, Maths/Biology. Revise weekly."
    }


# 🏠 HOME
@app.get("/")
def home():
    return {"message": "E Acad Backend Running 🚀"}
