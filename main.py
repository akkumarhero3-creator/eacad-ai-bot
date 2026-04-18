from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import requests, os, random, time, base64
from fastapi.middleware.cors import CORSMiddleware
from collections import deque

print("🔥 BACKEND STARTING...")

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 KEYS (SAFE)
API_KEYS = [os.getenv(f"GEMINI_KEY_{i}") for i in range(1,11)]
API_KEYS = [k for k in API_KEYS if k]

if not API_KEYS:
    print("❌ WARNING: No GEMINI API KEYS FOUND")

# 🧠 MEMORY + CACHE
student_memory = {}
cache = {}
last_request = {}

# 🧠 MODEL CACHE
AVAILABLE_MODELS = []
LAST_MODEL_FETCH = 0

# 🧠 QUEUE
queue = deque()
processing = False

# ✅ FIXED MODEL (IMPORTANT)
class Message(BaseModel):
    message: str = ""
    subject: str = ""
    image: Optional[str] = None
    user_id: str = "student1"

# 🚫 RATE LIMIT
def allow(user):
    now = time.time()
    if user in last_request and now - last_request[user] < 2:
        return False
    last_request[user] = now
    return True

# 🚫 ABUSE
def is_abusive(text):
    bad_words = ["idiot","stupid","fuck","shit","madarchod","chutiya","pagal"]
    return any(word in (text or "").lower() for word in bad_words)

# 🎯 DIFFICULTY
def detect_difficulty(q):
    q = q or ""
    if len(q) < 20:
        return "easy"
    elif len(q) < 60:
        return "medium"
    return "hard"

# 🔥 FETCH MODELS
def fetch_models(key):
    global AVAILABLE_MODELS, LAST_MODEL_FETCH

    if time.time() - LAST_MODEL_FETCH < 3600 and AVAILABLE_MODELS:
        return AVAILABLE_MODELS

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url, timeout=10).json()

        models = [
            m["name"].replace("models/", "")
            for m in res.get("models", [])
            if "generateContent" in str(m)
        ]

        models.sort(key=lambda x: "flash" not in x)

        AVAILABLE_MODELS = models
        LAST_MODEL_FETCH = time.time()

        return models

    except:
        return ["gemini-1.5-flash-latest"]

# 🧠 PROMPT
def build_prompt(q, level="medium"):
    return f"""
You are a top JEE/NEET teacher (PW / Allen level).

Speak in Hinglish.

Student Level: {level}

Format STRICTLY:

### Concept
Explain core idea

### Formula
Write needed formulas

### Step-by-step
Solve properly

### Final Answer
Final result with unit

### Exam Trick
Shortcut or quick method

If image:
- Read handwritten
- Understand diagram
- Solve

Rules:
- Use clean LaTeX like $F = ma$
- Avoid \\vec, \\text

Question: {q}
"""

# 🤖 GEMINI
def ask_gemini(prompt, image=None):

    keys = [k for k in API_KEYS if k]
    random.shuffle(keys)

    for key in keys:

        models = fetch_models(key)

        for model in models[:3]:

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

            parts = [{"text": prompt}]

            if image:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image
                    }
                })

            payload = {"contents": [{"parts": parts}]}

            for attempt in range(3):
                try:
                    res = requests.post(url, json=payload, timeout=20).json()

                    if "candidates" in res:
                        try:
                            return res["candidates"][0]["content"]["parts"][0]["text"]
                        except Exception as e:
                            print("Parse error:", e)
                            continue

                except Exception as e:
                    print("Request error:", e)
                    time.sleep(1)

    return None

# 🔁 OPENAI FALLBACK
def ask_openai(prompt):
    key = os.getenv("OPENAI_API_KEY")

    if not key:
        return "⚠️ Sab AI Teachers busy hai beta 😄"

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        ).json()

        return r["choices"][0]["message"]["content"]

    except:
        return "⚠️ All AI Teachers busy beta 😄"

# ⚙️ PROCESS
def process(msg):

    uid = msg.user_id or "student1"

    if not allow(uid):
        return "⏳ Arre beta 😄 thoda ruk!"

    cache_key = f"{msg.subject}:{msg.message}:{'img' if msg.image else 'text'}"

    if cache_key in cache:
        return cache[cache_key]

    level = student_memory.get(uid, "medium")

    if len(msg.message or "") < 15:
        level = "weak"
    elif len(msg.message or "") > 80:
        level = "strong"

    student_memory[uid] = level

    prompt = build_prompt(msg.message, level)

    reply = ask_gemini(prompt, msg.image)

    if not reply:
        reply = ask_openai(prompt)

    cache[cache_key] = reply

    return reply

# 🚀 CHAT
@app.post("/chat")
async def chat(
    message: str = Form(""),
    subject: str = Form(...),
    image: UploadFile = File(None),
    user_id: str = Form("student1")
):
    global processing

    if is_abusive(message):
        return {"reply": "Language sudhar beta nahito gabbar aayega to teri sari kundali kholke samne layega😄", "difficulty": "easy"}

    img_base64 = None

    if image:
        contents = await image.read()
        img_base64 = base64.b64encode(contents).decode("utf-8")

    msg = Message(
        message=message or "",
        subject=subject,
        image=img_base64,
        user_id=user_id or "student1"
    )

    queue.append(msg)

    if processing:
        return {"reply": "⏳ Queue mein hai beta 😄 thoda wait kar", "difficulty": "easy"}

    processing = True

    current = queue.popleft()

    diff = detect_difficulty(current.message)

    reply = process(current)

    processing = False

    return {"reply": reply, "difficulty": diff}

@app.get("/")
def home():
    return {"status": "E Acad AI Running 🚀"}
