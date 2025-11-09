import os
import base64
import json
import requests
from requests.exceptions import RequestException, Timeout, HTTPError

# По умолчанию работаем ТОЛЬКО на локальном анализе.
# Если захочешь вернуть OpenRouter — в Render Environment поставь AI_PROVIDER=OPENROUTER
AI_PROVIDER = os.environ.get("AI_PROVIDER", "LOCAL").upper()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "z-ai/glm-4.5-air:free"
OPENROUTER_TIMEOUT = 40  # должно быть меньше gunicorn timeout


def encode_file_to_base64(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------- Рекомендации по “дырам” в профиле ----------

def build_gap_recommendations(main_category, profile_summary):
    core_cats = ['research', 'social', 'creative', 'sports', 'competence']
    counts = {c: 0 for c in core_cats}

    if profile_summary and isinstance(profile_summary, dict):
        by_cat = profile_summary.get("by_category", {})
        for c, n in by_cat.items():
            if c in counts:
                counts[c] += n

    if main_category in counts:
        counts[main_category] += 1

    missing = [c for c in core_cats if counts[c] == 0]

    recs = []
    if 'social' in missing:
        recs.append("Add volunteering or social impact projects to show your social responsibility.")
    if 'research' in missing:
        recs.append("Add olympiads, research projects or academic competitions to strengthen your academic profile.")
    if 'creative' in missing:
        recs.append("Add creative or public speaking activities (debates, art, music, media).")
    if 'sports' in missing:
        recs.append("Add sports achievements or long-term sport involvement.")
    if 'competence' in missing:
        recs.append("Add leadership/mentoring or teamwork experiences to highlight key competencies.")

    if not recs:
        recs.append(
            "You already have a well-balanced profile. Focus on deeper, longer-term projects and leadership roles."
        )

    return recs[:3]


# ---------- Локальный fallback-анализ (без внешних зависимостей) ----------

def local_fallback_analysis(user_full_name, title, category_hint, description, profile_summary=None):
    text = f"{title or ''} {description or ''}".lower()

    # Категория
    if category_hint and category_hint != 'other':
        category = category_hint
    else:
        if any(w in text for w in ["олимпиад", "olymp", "competition", "contest", "hackathon", "research"]):
            category = "research"
        elif any(w in text for w in ["volunteer", "волонтер", "волонтёр", "ngo", "community service"]):
            category = "social"
        elif any(w in text for w in ["art", "music", "dance", "drawing", "creative", "debate", "mun"]):
            category = "creative"
        elif any(w in text for w in ["sport", "football", "basketball", "swimming", "tournament"]):
            category = "sports"
        elif any(w in text for w in ["leader", "leadership", "soft skills", "teamwork", "mentor"]):
            category = "competence"
        else:
            category = "other"

    # Масштаб
    if any(w in text for w in ["international", "междунар", "world", "global"]):
        scale = "international"
    elif any(w in text for w in ["national", "республикан", "country-wide"]):
        scale = "national"
    elif any(w in text for w in ["city", "regional", "обл", "город"]):
        scale = "city"
    else:
        scale = "school"

    # Роль
    if any(w in text for w in ["founder", "co-founder", "president", "captain", "chair", "leader"]):
        role_type = "leader"
    elif any(w in text for w in ["organizer", "organized", "организатор"]):
        role_type = "organizer"
    elif any(w in text for w in ["1st place", "winner", "gold", "grand prix", "призер", "призёр"]):
        role_type = "winner"
    else:
        role_type = "participant"

    # Длительность (очень грубо, но стабильно)
    duration_months = 1
    if any(w in text for w in ["6 months", "6 месяцев", "полгода"]):
        duration_months = 6
    if any(w in text for w in ["1 year", "12 months", "год", "12 месяцев"]):
        duration_months = 12

    scores = {
        "category": 20 if category in ["research", "competence"] else 15,
        "scale": {"school": 5, "city": 10, "national": 15, "international": 20}.get(scale, 5),
        "role": {"participant": 5, "winner": 15, "organizer": 12, "leader": 18}.get(role_type, 5),
        "duration": min(duration_months, 12) * (20 / 12),
    }
    total_score = round(sum(scores.values()), 1)

    feedback = (
        f"{user_full_name or 'Student'} has an achievement in the '{category}' track "
        f"at {scale} level as {role_type}. Estimated impact score: {total_score}."
    )

    recs = build_gap_recommendations(category, profile_summary)

    return {
        "category": category,
        "scale": scale,
        "role_type": role_type,
        "duration_months": duration_months,
        "scores": scores,
        "total_score": total_score,
        "feedback": feedback,
        "missing_recommendations": recs,
        "provider": "local_fallback",
    }


# ---------- OpenRouter (опционально, но не обязателен для работы) ----------

def call_openrouter_analyzer(user_full_name, title, category_hint, description, file_b64, profile_summary):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("No OPENROUTER_API_KEY")

    system_msg = (
        "You are SocGPA.AI, an expert evaluator for a student Social GPA platform.\n"
        "Return ONLY JSON with keys: "
        "{category, scale, role_type, duration_months, scores, total_score, feedback, missing_recommendations}."
    )

    user_payload = {
        "student_name": user_full_name,
        "title": title,
        "category_hint": category_hint,
        "description": description,
        "profile_summary": profile_summary or {},
    }

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps(user_payload)},
    ]

    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    if file_b64:
        data["attachments"] = [
            {
                "type": "image",
                "data": file_b64,
                "mime_type": "image/png",
            }
        ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Referer": "https://socgpa.ai",
        "X-Title": "SocGPA.AI",
    }

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=data,
            timeout=OPENROUTER_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (Timeout, HTTPError, RequestException, KeyError, ValueError) as e:
        # Любая проблема -> пусть выше решит уйти на fallback.
        print("AI error (OpenRouter), will use local fallback instead:", repr(e))
        raise

    # Заполняем дефолты, чтобы не было KeyError
    defaults = {
        "category": "other",
        "scale": "school",
        "role_type": "participant",
        "duration_months": 0,
        "scores": {
            "category": 10,
            "scale": 10,
            "role": 10,
            "duration": 10,
        },
        "total_score": 40,
        "feedback": "Solid achievement.",
        "missing_recommendations": [],
    }
    for k, v in defaults.items():
        result.setdefault(k, v)

    result["provider"] = "openrouter"
    return result


# ---------- Главная точка входа (гарантированный результат) ----------

def analyze_achievement_with_ai(
    user_full_name,
    title,
    category,
    description,
    file_path=None,
    profile_summary=None
):
    file_b64 = encode_file_to_base64(file_path) if file_path else None
    desc = description or ""

    # 1) Опционально пробуем OpenRouter, только если ЯВНО включен и есть ключ.
    use_remote = (
        AI_PROVIDER == "OPENROUTER"
        and bool(OPENROUTER_API_KEY)
    )

    if use_remote:
        try:
            return call_openrouter_analyzer(
                user_full_name,
                title,
                category,
                desc,
                file_b64,
                profile_summary,
            )
        except Exception:
            # Любая ошибка -> просто лог и идём на локальный анализ.
            pass

    # 2) Всегда делаем локальный анализ как основной / резервный вариант.
    try:
        return local_fallback_analysis(
            user_full_name,
            title,
            category,
            desc,
            profile_summary,
        )
    except Exception as e:
        # На всякий пожарный: даже если внутри fallback что-то сломают,
        # пользователь всё равно получит валидный JSON, а не 500.
        print("CRITICAL: local_fallback_analysis failed:", repr(e))
        return {
            "category": category or "other",
            "scale": "school",
            "role_type": "participant",
            "duration_months": 0,
            "scores": {
                "category": 10,
                "scale": 10,
                "role": 10,
                "duration": 10,
            },
            "total_score": 40,
            "feedback": "Achievement recorded. (safe fallback)",
            "missing_recommendations": [],
            "provider": "safe_minimal_fallback",
        }
