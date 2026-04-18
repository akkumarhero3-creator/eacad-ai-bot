from fastapi import FastAPI
from pydantic import BaseModel
import requests, os, random, time
from fastapi.middleware.cors import CORSMiddleware
from collections import deque

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 API KEYS
API_KEYS = [os.getenv(f"GEMINI_KEY_{i}") for i in range(1,11)]

# 🧠 MEMORY
student_memory = {}
cache = {}
last_request = {}

# 🧠 MODEL CACHE
AVAILABLE_MODELS = []
LAST_MODEL_FETCH = 0

# 🧠 QUEUE
queue = deque()
processing = False

# 📩 REQUEST MODEL
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"

# 🚫 RATE LIMIT
def allow(user):
    now = time.time()
    if user in last_request and now - last_request[user] < 2:
        return False
    last_request[user] = now
    return True

# 🚫 ABUSE FILTER
def is_abusive(text):
    bad_words = ["idiot","stupid","fuck","shit","madarchod","chutiya","pagal"]
    return any(word in text.lower() for word in bad_words)

# 🎯 DIFFICULTY
def detect_difficulty(q):
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
def prompt_builder(q):
    return f"""
You are a JEE/NEET teacher.

Explain in Hinglish (fun + friendly 😄)

Format STRICTLY:

### Concept
### Formula
### Step-by-step
### Final Answer

Question: {q}
"""

# 🤖 GEMINI (ROTATION + RETRY)
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

            for _ in range(3):
                try:
                    res = requests.post(url, json=payload, timeout=20).json()

                    if "candidates" in res:
                        return res["candidates"][0]["content"]["parts"][0]["text"]

                    if "error" in res:
                        msg = res["error"]["message"].lower()

                        if "quota" in msg or "limit" in msg:
                            break

                        if "overloaded" in msg:
                            time.sleep(2)
                            continue

                        break

                except:
                    time.sleep(1)

    return None

# 🔁 OPENAI FALLBACK
def ask_openai(prompt):
    key = os.getenv("OPENAI_API_KEY")

    if not key:
        return "⚠️ Sab AI busy hai 😄"

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20).json()
        return r["choices"][0]["message"]["content"]
    except:
        return "⚠️ All AI systems busy 😄"

# ⚙️ PROCESS
def process(msg):

    if not allow(msg.user_id):
        return "⏳ Arre bhai 😄 thoda ruk!"

    cache_key = f"{msg.subject}:{msg.message}"

    if cache_key in cache:
        return cache[cache_key]

    prompt = prompt_builder(msg.message)

    reply = ask_gemini(prompt, msg.image)

    if not reply:
        reply = ask_openai(prompt)

    cache[cache_key] = reply

    return reply

# 🚀 CHAT
@app.post("/chat")
def chat(msg: Message):
    global processing

    # 🚫 abuse check
    if is_abusive(msg.message):
        return {"reply": "Language sudhar bhai 😄", "difficulty": "easy"}

    queue.append(msg)

    if processing:
        return {"reply": "⏳ Queue mein hai bhai 😄", "difficulty": "easy"}

    processing = True

    current = queue.popleft()

    diff = detect_difficulty(current.message)

    reply = process(current)

    processing = False

    return {"reply": reply, "difficulty": diff}

# 🔥 CHECK KEYS
@app.get("/check-keys")
def check_keys():

    results = []

    for i, key in enumerate(API_KEYS, start=1):

        if not key:
            results.append({"key": i, "status": "❌ Missing"})
            continue

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            res = requests.get(url, timeout=10).json()

            if "models" in res:
                results.append({"key": i, "status": "✅ Working"})
            else:
                results.append({"key": i, "status": "⚠️ Issue"})

        except Exception as e:
            results.append({"key": i, "status": str(e)})

    return {"keys": results}

# 🏠 HOME
@app.get("/")
def home():
    return {"status": "E Acad AI Running 🚀"}
