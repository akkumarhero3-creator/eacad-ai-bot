from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

GEMINI_API_KEY = "AQ.Ab8RN6LhCSvlT3Io8G1BLG1O_e78uQFWv0PdufWiUPwKH-QqUQ"

class Message(BaseModel):
    message: str
    subject: str

def build_prompt(subject, question):

    rules = """
You are an expert teacher for Class 8–12, JEE and NEET.
Explain clearly step-by-step.

If question is irrelevant:
Reply exactly:
"Ye chacha tula samajhta ka nahi 😤 Ja jaaun abhyas kar 📚🔥"
"""

    teachers = {
        "physics": "Avinash 2.0 (Physics expert, use formulas)",
        "maths": "Dharmentra 2.0 (Maths expert, step-by-step solving)",
        "chemistry": "Abhishek 2.0 (Chemistry expert, NCERT based)",
        "biology": "Ashutosh 2.0 (Biology expert, simple explanation)"
    }

    return f"{rules}\nYou are {teachers[subject]}\nQuestion: {question}"

def ask_ai(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    res = requests.post(url, json={
        "contents":[{"parts":[{"text":prompt}]}]
    })

    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "⚠️ Error, try again"

@app.post("/chat")
def chat(msg: Message):
    reply = ask_ai(build_prompt(msg.subject, msg.message))
    return {"reply": reply}