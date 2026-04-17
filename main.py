from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# memory (basic weak topic tracking)
student_memory = {}

class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "default"


def build_prompt(subject, question, weak_topics):

    return f"""
You are an expert teacher for Class 8–12, JEE, NEET.

Student weak topics: {weak_topics}

Respond in structured format:

### Concept
### Formula
### Step-by-step Solution
### Final Answer

Rules:
- Use LaTeX for equations (example: \\(F=ma\\))
- Explain diagrams clearly if image present
- Keep explanation simple but exam-level

If irrelevant:
"Ye chacha tula samajhta ka nahi 😤 Ja jaaun abhyas kar 📚🔥"

Question: {question}
"""


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


@app.post("/chat")
def chat(msg: Message):

    user = msg.user_id

    if user not in student_memory:
        student_memory[user] = []

    weak_topics = ", ".join(student_memory[user])

    prompt = build_prompt(msg.subject, msg.message, weak_topics)

    reply = ask_ai(prompt, msg.image)

    # simple weak topic detection
    if "force" in msg.message.lower():
        student_memory[user].append("Mechanics")

    return {"reply": reply}
