from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

# ✅ CORS (required for Wix)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Allow frontend access (Wix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 GET API KEY SECURELY (NOT hardcoded)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# 📩 Request format
class Message(BaseModel):
    message: str
    subject: str


# 🧠 Teacher Prompt Logic
def build_prompt(subject, question):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain answers clearly, step-by-step, and in simple language.

If the question is NOT related to studies, reply EXACTLY:
"Ye chacha tula samajhta ka nahi 😤 E Acad Sutra study sathi aahe. Ja jaaun abhyas kar 📚🔥"
"""

    teachers = {
        "physics": "Avinash 2.0 (Physics expert, use formulas and concepts)",
        "maths": "Dharmentra 2.0 (Maths expert, solve step-by-step clearly)",
        "chemistry": "Abhishek 2.0 (Chemistry expert, NCERT-based explanation)",
        "biology": "Ashutosh 2.0 (Biology expert, simple explanation)"
    }

    teacher = teachers.get(subject, "General Teacher")

    return f"{rules}\nYou are {teacher}\n\nQuestion: {question}"


# 🤖 Gemini API Call (latest model)
def ask_ai(prompt):

    if not GEMINI_API_KEY:
        return "⚠️ API Key not found."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()

        print(result)

        if "candidates" in result:
            return result["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in result:
            return f"⚠️ Gemini Error: {result['error']['message']}"

        else:
            return str(result)

    except Exception as e:
        return f"⚠️ Exception: {str(e)}"


# 🚀 Main API
@app.post("/chat")
def chat(msg: Message):

    prompt = build_prompt(msg.subject, msg.message)
    reply = ask_ai(prompt)

    return {"reply": reply}


# 🏠 Test route
@app.get("/")
def home():
    return {"message": "E Acad AI Backend Running 🚀"}
