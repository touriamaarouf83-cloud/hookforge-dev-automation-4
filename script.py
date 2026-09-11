import os
import random
import time
import requests
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


# ============================================================
# HELPER: call Gemini with retry/backoff on transient errors
# ============================================================

def generate_with_retry(model, prompt, max_attempts=4):
    """Calls model.generate_content with exponential backoff on
    transient errors (rate limits, server overload). Raises on the
    final failed attempt or on non-transient errors."""
    for attempt in range(1, max_attempts + 1):
        try:
            return model.generate_content(prompt)
        except (google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
                google_exceptions.InternalServerError) as e:
            if attempt == max_attempts:
                raise
            wait = 2 ** attempt  # 2s, 4s, 8s, 16s...
            print(f"⏳ Gemini transient error ({type(e).__name__}); retry {attempt}/{max_attempts - 1} in {wait}s...")
            time.sleep(wait)


# ============================================================
# 1. CONFIGURATION GEMINI
# ============================================================

gemini_key = os.environ.get("GEMINI_API_KEY")

if not gemini_key:
    print("❌ ERROR: GEMINI_API_KEY is missing!")
    exit(1)

genai.configure(api_key=gemini_key)

model = genai.GenerativeModel("models/gemini-3.6-flash")


# ============================================================
# 2. CHOOSE A COPYWRITING FRAMEWORK
# ============================================================

frameworks = [
    "Logic Gap",
    "Negative Stake",
    "PAS Framework",
    "AIDA Model",
    "The Curiosity Loop",
    "Open Loop Hook"
]

chosen_framework = random.choice(frameworks)

print(f"🧠 Selected framework: {chosen_framework}")


# ============================================================
# 3. GENERATE ARTICLE
# ============================================================

prompt = f"""
Write an expert, highly engaging article of around 300 words
for tech content creators.

Focus on the video copywriting framework called:
"{chosen_framework}"

Requirements:
- Casual and punchy writing style
- Useful and practical
- Written for YouTubers and tech content creators
- Explain the framework clearly
- Include practical examples
- Do not sound like an advertisement
- Return the response in clean Markdown
- Do NOT generate a title

At the very end, include this exact CTA:

Automate your video scripts for free at
[HookForge AI](https://hook-forge-prime.base44.app).
"""

try:
    response = generate_with_retry(model, prompt)

    article_body = response.text.strip()

    if not article_body:
        raise ValueError("Gemini returned an empty response.")

    print("✅ Gemini successfully generated the article text.")

except Exception as e:
    print(f"❌ Gemini Generation Failed: {e}")
    exit(1)


# ============================================================
# 4. UPDATE README.md
# ============================================================

try:
    with open("README.md", "w", encoding="utf-8") as file:
        file.write(article_body)

    print("✅ README.md file updated.")

except Exception as e:
    print(f"❌ Failed to update README.md: {e}")
    exit(1)


# ============================================================
# 5. GET DEV.TO API KEY
# ============================================================

DEV_TO_API_KEY = os.environ.get("DEV_TO_API_KEY")

if not DEV_TO_API_KEY:
    print("❌ ERROR: DEV_TO_API_KEY is missing in GitHub Secrets!")
    exit(1)

api_key_clean = DEV_TO_API_KEY.strip()


# ============================================================
# 6. GENERATE ARTICLE TITLE
# ============================================================

title_prompt = f"""
Generate a short, catchy headline under 10 words
about the video copywriting framework "{chosen_framework}".

Requirements:
- No quotation marks
- No emojis
- Clear and interesting
- Suitable for DEV.to
- Do not mention HookForge AI
"""

try:
    title_response = generate_with_retry(model, title_prompt)

    article_title = (
        title_response.text
        .strip()
        .replace('"', "")
        .replace("'", "")
    )

    if not article_title:
        raise ValueError("Gemini returned an empty title.")

except Exception as e:
    print(f"⚠️ Title generation failed: {e}")

    article_title = (
        f"Mastering Video Hooks with {chosen_framework}"
    )


print(f"📝 Article title: {article_title}")


# ============================================================
# 7. DEV.TO API CONFIGURATION
# ============================================================

# Correct DEV.to API endpoint for creating articles
url = "https://dev.to/api/articles"

headers = {
    "api-key": api_key_clean,
    "Content-Type": "application/json",
    "User-Agent": "HookForgeAI-Automated-Publisher/1.0"
}


# ============================================================
# 8. ARTICLE DATA
# ============================================================

data = {
    "article": {
        "title": article_title,
        "body_markdown": article_body,
        "published": True,  # 🚀 تم التعديل للنشر الحي والمباشر فوراً تلقائياً
        "tags": [
            "youtube",
            "ai"
        ]
    }
}



# ============================================================
# 9. PUBLISH TO DEV.TO
# ============================================================

print("🚀 Sending article to DEV.to...")

try:

    res = requests.post(
        url,
        json=data,
        headers=headers,
        timeout=30
    )

    print(f"🔹 Response HTTP Code: {res.status_code}")


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if res.status_code == 201:

        result = res.json()

        print("📝 DRAFT CREATED on DEV.to — review and publish manually.")

        article_url = result.get("url")

        if article_url:
            print(f"🔗 Draft URL (edit before publishing): {article_url}")

        article_id = result.get("id")

        if article_id:
            print(f"🆔 Article ID: {article_id}")


    # --------------------------------------------------------
    # UNAUTHORIZED
    # --------------------------------------------------------

    elif res.status_code == 401:

        print("❌ ERROR 401: DEV.to rejected the API key.")
        print("Check your DEV_TO_API_KEY GitHub Secret.")
        print(f"🔹 Response: {res.text[:500]}")

        exit(1)


    # --------------------------------------------------------
    # VALIDATION ERROR
    # --------------------------------------------------------

    elif res.status_code == 422:

        print("❌ ERROR 422: DEV.to rejected the article data.")
        print(f"🔹 Response: {res.text[:1000]}")

        exit(1)


    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    elif res.status_code == 429:

        print("⏳ ERROR 429: DEV.to rate limit exceeded.")
        print(f"🔹 Response: {res.text[:500]}")

        exit(1)


    # --------------------------------------------------------
    # OTHER ERROR
    # --------------------------------------------------------

    else:

        print(
            f"❌ DEV.to Server Rejected Request "
            f"with Code {res.status_code}"
        )

        print(f"🔹 Response: {res.text[:1000]}")

        exit(1)


except requests.exceptions.Timeout:

    print("❌ ERROR: Request to DEV.to timed out.")
    exit(1)


except requests.exceptions.RequestException as e:

    print(f"❌ ERROR: DEV.to request failed: {e}")
    exit(1)


except Exception as e:

    print(f"❌ Unexpected error: {e}")
    exit(1)
