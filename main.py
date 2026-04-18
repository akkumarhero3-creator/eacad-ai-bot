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

# 🔥 FETCH MODELS
def fetch_models(key):
    global AVAILABLE_MODELS, LAST_MODEL_FETCH

    if time.time() - LAST_MODEL_FETCH < 3600 and AVAILABLE_MODELS:
        return AVAILABLE_MODELS

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url).json()

        models = [m["name"].replace("models/","") for m in res.get("models",[])
                  if "generateContent" in str(m)]

        models.sort(key=lambda x: "flash" not in x)

        AVAILABLE_MODELS = models
        LAST_MODEL_FETCH = time.time()

        return models
    except:
        return ["gemini-1.5-flash-latest"]

# 🧠 PROMPT
def prompt_builder(q):
    return f"""
Explain in Hinglish (fun + friendly 😄)

### Concept
### Formula
### Step-by-step
### Final Answer

Question: {q}
"""

# 🤖 GEMINI + RETRY
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
                    "inline_data":{"mime_type":"image/jpeg","data":image}
                })

            payload = {"contents":[{"parts":parts}]}

            for _ in range(3):
                try:
                    res = requests.post(url,json=payload,timeout=20).json()

                    if "candidates" in res:
                        return res["candidates"][0]["content"]["parts"][0]["text"]

                    if "error" in res:
                        msg = res["error"]["message"].lower()

                        if "quota" in msg or "limit" in msg:
                            break
                        if "overloaded" in msg or "high demand" in msg:
                            time.sleep(2)
                            continue

                except:
                    time.sleep(1)

    return None

# 🔁 OPENAI FALLBACK
def ask_openai(prompt):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "⚠️ Server busy 😄"

    url = "https://api.openai.com/v1/chat/completions"

    headers = {"Authorization": f"Bearer {key}"}

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role":"user","content":prompt}]
    }

    try:
        r = requests.post(url, headers=headers, json=payload).json()
        return r["choices"][0]["message"]["content"]
    except:
        return "⚠️ All AI busy 😄"

# ⚙️ PROCESS
def process(msg):

    if not allow(msg.user_id):
        return "⏳ Slow down bhai 😄"

    key = f"{msg.subject}:{msg.message}"

    if key in cache:
        return cache[key]

    prompt = prompt_builder(msg.message)

    reply = ask_gemini(prompt, msg.image)

    if not reply:
        reply = ask_openai(prompt)

    cache[key] = reply

    return reply

# 🚀 CHAT
@app.post("/chat")
def chat(msg: Message):
    global processing

    queue.append(msg)

    if processing:
        return {"reply":"⏳ Queue mein hai 😄 wait..."}

    processing = True
    m = queue.popleft()

    reply = process(m)

    processing = False

    return {"reply": reply}

# 🏠
@app.get("/")
def home():
    return {"status":"running 🚀"}
