from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import random
import time
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

# 🔥 MULTIPLE API KEYS (10 KEYS)
API_KEYS = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
    os.getenv("GEMINI_KEY_4"),
    os.getenv("GEMINI_KEY_5"),
    os.getenv("GEMINI_KEY_6"),
    os.getenv("GEMINI_KEY_7"),
    os.getenv("GEMINI_KEY_8"),
    os.getenv("GEMINI_KEY_9"),
    os.getenv("GEMINI_KEY_10"),
]

# 🧠 MEMORY + CACHE
student_memory = {}
cache = {}
last_request = {}

# 📩 MODEL
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"


# 🚫 RATE LIMIT (ANTI SPAM)
def allow_request(user_id):
    now = time.time()

    if user_id in last_request:
        if now - last_request[user_id] < 2:
            return False

    last_request[user_id] = now
    return True


# 🔥 PROMPT
def build_prompt(subject, question, weak_topics):
    return f"""
You are a top JEE/NEET teacher.

Speak in Hinglish (Hindi + English mix).
Be friendly and motivating 😄

Format STRICTLY:

### Concept
Explain simply

### Formula
Use proper equations

### Step-by-step
Teach clearly

### Final Answer
Short crisp answer

If outside syllabus:
"Arre bhai out of syllabus hai ye, 😄 yaha sirf JEE NEET Ki padhai hoti hai!"

Question: {question}
"""


# 🤖 AI FUNCTION (MULTI-KEY ROTATION)
def ask_ai(prompt, image=None):

    keys = [k for k in API_KEYS if k]
    random.shuffle(keys)  # 🔥 load balance

    for key in keys:

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"

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
            response = requests.post(url, json=payload, timeout=20)
            result = response.json()

            print("KEY USED:", key[:6], result)

            # ✅ SUCCESS
            if "candidates" in result:
                return result["candidates"][0]["content"]["parts"][0]["text"]

            # ⚠️ HANDLE ERRORS
            if "error" in result:
                msg = result["error"]["message"].lower()

                if "quota" in msg or "limit" in msg:
                    continue  # 🔄 try next key

                return f"⚠️ {result['error']['message']}"

        except Exception as e:
            print("Error:", e)
            continue

    return "⚠️ Sab AI teachers busy hai 😄 thode time baad try kar"


# 🚀 CHAT
@app.post("/chat")
def chat(msg: Message):

    user = msg.user_id

    # 🚫 RATE LIMIT
    if not allow_request(user):
        return {"reply": "⏳ Arre bhai 😄 thoda ruk 2 sec!"}

    # 📦 CACHE CHECK
    cache_key = f"{msg.subject}:{msg.message}"

    if cache_key in cache:
        return {"reply": cache[cache_key]}

    # 🧠 USER MEMORY
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

    # 🧠 PROMPT
    prompt = build_prompt(msg.subject, msg.message, weak_topics)

    # 🤖 AI CALL
    reply = ask_ai(prompt, msg.image)

    # 💾 SAVE CACHE
    cache[cache_key] = reply

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


# 🏠 HOME
@app.get("/")
def home():
    return {"message": "E Acad AI Running 🚀"}
