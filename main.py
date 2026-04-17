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

# 🔐 API KEY (from Render)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🧠 In-memory storage (simple database)
student_memory = {}
student_analytics = {}


# 📩 Request model
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    history: list = []


# 🧠 Prompt builder
def build_prompt(subject, question, history):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain step-by-step in simple language.

If NOT study related, reply:
"Ye chacha tula samajhta ka nahi 😤 Ja jaaun abhyas kar 📚🔥"
"""

    teacher_map = {
        "physics": "Avinash 2.0 (Physics expert)",
        "maths": "Dharmentra 2.0 (Maths expert)",
        "chemistry": "Abhishek 2.0 (Chemistry expert)",
        "biology": "Ashutosh 2.0 (Biology expert)"
    }

    teacher = teacher_map.get(subject, "Teacher")

    # 🧠 Add history context
    history_text = ""
    for h in history[-5:]:
        history_text += f"{h['role']}: {h['text']}\n"

    return f"{rules}\nYou are {teacher}\n\nConversation:\n{history_text}\nQuestion: {question}"


# 🤖 Gemini TEXT
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
        else:
            return "⚠️ AI error"

    except Exception as e:
        return f"⚠️ {str(e)}"


# 🤖 Gemini IMAGE
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

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "⚠️ Image AI error"

    except Exception as e:
        return f"⚠️ {str(e)}"


# 🚀 MAIN CHAT
@app.post("/chat")
def chat(msg: Message):

    prompt = build_prompt(msg.subject, msg.message, msg.history)

    # 📸 If image present
    if msg.image:
        reply = ask_image(prompt, msg.image)
    else:
        reply = ask_text(prompt)

    # 📊 simple analytics (count messages per subject)
    student_analytics.setdefault("student1", {})
    student_analytics["student1"][msg.subject] = student_analytics["student1"].get(msg.subject, 0) + 1

    return {"reply": reply}


# 📊 ANALYTICS API
@app.get("/analytics/{student}")
def analytics(student: str):

    data = student_analytics.get(student, {
        "physics": 2,
        "maths": 1,
        "chemistry": 1,
        "biology": 0
    })

    return {"data": data}


# 📅 STUDY PLAN
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


# 🏠 TEST
@app.get("/")
def home():
    return {"message": "E Acad AI Backend Running 🚀"}
