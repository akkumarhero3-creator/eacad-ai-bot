from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import requests, os, random, time, base64
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

# 🔑 LOAD MULTIPLE KEYS
API_KEYS = [os.getenv(f"GEMINI_KEY_{i}") for i in range(1,11)]

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

# 📩 REQUEST MODEL
class Message(BaseModel):
    message: str
    subject: str
    image: str = None
    user_id: str = "student1"

# 🚫 RATE LIMIT (2 sec/user)
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

# 🎯 DIFFICULTY DETECTION
def detect_difficulty(q):
    if len(q) < 20:
        return "easy"
    elif len(q) < 60:
        return "medium"
    return "hard"

# 🔥 FETCH AVAILABLE MODELS
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

# 🧠 PROMPT (UPGRADED FOR IMAGE + DIAGRAM UNDERSTANDING)
def build_prompt(q):
    return f"""
You are a top JEE/NEET teacher.

Speak in Hinglish (Hindi + English mix).
Be friendly, energetic and slightly funny 😄

Style:
- Use phrases like "arre beta", "samjha kya?", "easy hai"

Format STRICTLY:

### Concept
Explain simply

### Formula
Use proper equations

### Step-by-step
Teach like real teacher

### Final Answer
Short crisp answer

----------------------------------------

If image is provided:

1. Carefully read handwritten text (ignore noise/scribbles)
2. Convert it into a clear question internally
3. If diagram is present:
   - Understand it properly (forces, circuit, rays, graph etc.)
   - Use it in solving
   - Explain in words (no drawing)

4. If graph:
   - Identify slope/intercept/area

5. If physics diagram:
   - Identify forces/directions/components

6. If circuit:
   - Identify connections and apply laws

----------------------------------------

Rules:
- DO NOT say "image shows"
- DO NOT output raw extracted text
- Solve directly like a teacher
- Use clean LaTeX like $F = ma$
- Avoid \\vec, \\text

----------------------------------------

Question: {q}
"""

# 🤖 GEMINI ENGINE (UNCHANGED LOGIC + SAFE HANDLING)
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
                        except:
                            continue

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

# ⚙️ PROCESS ENGINE (CACHE FIX ADDED)
def process(msg):

    if not allow(msg.user_id):
        return "⏳ Arre beta 😄 thoda ruk!"

    cache_key = f"{msg.subject}:{msg.message}:{'img' if msg.image else 'text'}"

    if cache_key in cache:
        return cache[cache_key]

    prompt = build_prompt(msg.message)

    reply = ask_gemini(prompt, msg.image)

    if not reply:
        reply = ask_openai(prompt)

    cache[cache_key] = reply

    return reply

# 🚀 CHAT (ONLY IMAGE SUPPORT ADDED)
@app.post("/chat")
async def chat(
    message: str = Form(""),
    subject: str = Form(...),
    image: UploadFile = File(None),
    user_id: str = Form("student1")
):
    global processing

    if is_abusive(message):
        return {"reply": "Language sudhar beta nahito gabbar aa jaega aur teri puri kundali khol dega sabke samne 😄", "difficulty": "easy"}

    # ✅ IMAGE FIX
    img_base64 = None
    if image:
        contents = await image.read()
        img_base64 = base64.b64encode(contents).decode("utf-8")

    msg = Message(
        message=message,
        subject=subject,
        image=img_base64,
        user_id=user_id
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

# 🔍 CHECK KEYS
@app.get("/check-keys")
def check_keys():
    results = []
    for i, key in enumerate(API_KEYS, 1):
        if not key:
            results.append({"key": i, "status": "❌ Missing"})
            continue
        try:
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}").json()
            if "models" in r:
                results.append({"key": i, "status": "✅ Working"})
            else:
                results.append({"key": i, "status": "⚠️ Issue"})
        except Exception as e:
            results.append({"key": i, "status": str(e)})
    return {"keys": results}

@app.get("/")
def home():
    return {"status": "E Acad AI Running 🚀"}
