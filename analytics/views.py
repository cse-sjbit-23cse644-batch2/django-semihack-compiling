import csv
import io
import json
import os

import pandas as pd
from django.contrib import messages
from django.db.models import Avg, Count, StdDev
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from django.conf import settings
from .models import EmotionalProfile, ResultRecord, Student, Subject, WellnessChatMessage

# Load .env file when running locally (ignored gracefully if not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# OpenAI client — works on Replit (managed proxy) and locally (OPENAI_API_KEY)
# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
try:
    from openai import OpenAI

    _replit_key  = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    _replit_url  = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    _local_key   = os.environ.get("OPENAI_API_KEY")

    if _replit_key and _replit_url:
        # Running on Replit — use managed proxy (no billing, no key management)
        _openai_client = OpenAI(api_key=_replit_key, base_url=_replit_url)
    elif _local_key:
        # Running locally — use standard OpenAI endpoint
        _openai_client = OpenAI(api_key=_local_key)
    else:
        _openai_client = None
except Exception:
    _openai_client = None


# ---------------------------------------------------------------------------
# Mock data helpers (used until real CSV data has been uploaded)
# ---------------------------------------------------------------------------

DEFAULT_SUBJECTS = [
    {"name": "Database Management Systems", "code": "CS301", "credits": 4,
     "marks": 78, "max_marks": 100, "grade": "A", "band": "strong"},
    {"name": "Operating Systems", "code": "CS302", "credits": 4,
     "marks": 52, "max_marks": 100, "grade": "C", "band": "weak"},
    {"name": "Design & Analysis of Algorithms", "code": "CS303", "credits": 4,
     "marks": 71, "max_marks": 100, "grade": "B+", "band": "moderate"},
    {"name": "Computer Networks", "code": "CS304", "credits": 3,
     "marks": 64, "max_marks": 100, "grade": "B", "band": "moderate"},
    {"name": "Web Technology", "code": "CS305", "credits": 3,
     "marks": 82, "max_marks": 100, "grade": "A", "band": "strong"},
    {"name": "Software Engineering", "code": "CS306", "credits": 3,
     "marks": 38, "max_marks": 100, "grade": "F", "band": "critical"},
]


def _band_meta(band):
    return {
        "strong": {"color": "#22C55E", "label": "Strong"},
        "moderate": {"color": "#F59E0B", "label": "Moderate"},
        "weak": {"color": "#EF4444", "label": "Weak"},
        "critical": {"color": "#6C3CE1", "label": "Critical"},
    }.get(band, {"color": "#6B7280", "label": "Unknown"})


def _get_student():
    """Retrieve the default student from DB or create from defaults."""
    s, created = Student.objects.get_or_create(
        student_id="2021CS042",
        defaults={
            "name": "Akanksha Tiwary",
            "email": "akanksha.tiwary@university.edu",
            "phone": "+91 98765 43210",
            "course": "Computer Science Engineering",
            "department": "Computer Science",
            "semester": 6,
            "roll_no": "CSE-042",
            "admission_year": "2021",
            "target_cgpa": 8.50,
        }
    )
    return s


def _shell_context(active, page_title, page_subtitle=""):
    return {
        "active_page": active,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "student": _get_student(),
        "notification_count": 3,
    }


# ---------------------------------------------------------------------------
# PAGE 1 — Dashboard
# ---------------------------------------------------------------------------

def dashboard(request):
    helix_subjects = []
    for s in DEFAULT_SUBJECTS:
        meta = _band_meta(s["band"])
        helix_subjects.append({**s, "color": meta["color"], "band_label": meta["label"]})

    backlog_subjects = [
        {"name": "Operating Systems", "risk": 80, "level": "High", "color": "#EF4444"},
        {"name": "Database Management", "risk": 45, "level": "Medium", "color": "#F59E0B"},
        {"name": "Computer Networks", "risk": 25, "level": "Low", "color": "#22C55E"},
    ]

    recommendations = [
        {"title": "Revise OS", "subtitle": "Deadlock concepts",
         "btn_label": "View Material", "btn_variant": "primary", "icon": "book"},
        {"title": "Improve Attendance", "subtitle": "You are below class avg.",
         "btn_label": "Check Details", "btn_variant": "outline", "icon": "calendar"},
        {"title": "Manage Stress", "subtitle": "Take 10 min meditation",
         "btn_label": "Start Now", "btn_variant": "success", "icon": "heart"},
        {"title": "Complete Assignments", "subtitle": "2 pending submissions",
         "btn_label": "View Now", "btn_variant": "warning", "icon": "clipboard"},
    ]

    semester_trend = {
        "labels": ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"],
        "values": [5.0, 5.5, 6.4, 6.9, 7.1, 7.24],
    }

    student = _get_student()
    target = student.target_cgpa
    target_diff = target - student.current_cgpa
    base_factor = target_diff * 12
    whatif_subjects = [
        {"name": "DBMS", "marks": max(40, min(100, round(65 + base_factor)))},
        {"name": "Operating Systems", "marks": max(40, min(100, round(60 + base_factor)))},
        {"name": "Design & Analysis of Alg.", "marks": max(40, min(100, round(68 + base_factor)))},
        {"name": "Computer Networks", "marks": max(40, min(100, round(62 + base_factor)))},
        {"name": "Web Technology", "marks": max(40, min(100, round(60 + base_factor)))},
    ]

    ctx = _shell_context("dashboard", "Dashboard")
    emotional_score, emotional_wellness_label, _ = _compute_wellness_score(
        student.student_id
    )
    ctx.update({
        "current_cgpa": student.current_cgpa,
        "target_cgpa": target,
        "subjects_left": 15,
        "semesters_left": 3,
        "backlog_risk_label": "High",
        "backlog_risk_count": 2,
        "helix_subjects_json": json.dumps(helix_subjects),
        "backlog_subjects": backlog_subjects,
        "recommendations": recommendations,
        "semester_trend_json": json.dumps(semester_trend),
        "whatif_subjects": whatif_subjects,
        "emotional_score": emotional_score,
        "emotional_wellness_label": emotional_wellness_label,
    })
    return render(request, "pages/dashboard.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 2 — My Profile
# ---------------------------------------------------------------------------

def my_profile(request):
    ctx = _shell_context("my-profile", "My Profile")
    student = ctx["student"]
    ctx.update({
        "current_cgpa": student.current_cgpa,
        "target_cgpa": student.target_cgpa,
        "attendance": 78,
        "subjects_done": 24,
        "subjects": DEFAULT_SUBJECTS,
    })
    return render(request, "pages/my_profile.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 3 / 8 — CGPA Planner / What-If Compiler (same component)
# ---------------------------------------------------------------------------

def _cgpa_planner_context(active, title):
    scenarios = {
        "minimum": [
            {"name": "DBMS", "credits": 4, "marks": 58, "base_marks": 58, "feasibility": "Easy"},
            {"name": "Operating Systems", "credits": 4, "marks": 62, "base_marks": 62, "feasibility": "Moderate"},
            {"name": "DAA", "credits": 4, "marks": 60, "base_marks": 60, "feasibility": "Easy"},
            {"name": "Computer Networks", "credits": 3, "marks": 55, "base_marks": 55, "feasibility": "Easy"},
            {"name": "Web Technology", "credits": 3, "marks": 50, "base_marks": 50, "feasibility": "Easy"},
        ],
        "balanced": [
            {"name": "DBMS", "credits": 4, "marks": 72, "base_marks": 72, "feasibility": "Moderate"},
            {"name": "Operating Systems", "credits": 4, "marks": 75, "base_marks": 75, "feasibility": "Moderate"},
            {"name": "DAA", "credits": 4, "marks": 78, "base_marks": 78, "feasibility": "Moderate"},
            {"name": "Computer Networks", "credits": 3, "marks": 70, "base_marks": 70, "feasibility": "Moderate"},
            {"name": "Web Technology", "credits": 3, "marks": 68, "base_marks": 68, "feasibility": "Moderate"},
        ],
        "best": [
            {"name": "DBMS", "credits": 4, "marks": 88, "base_marks": 88, "feasibility": "Hard"},
            {"name": "Operating Systems", "credits": 4, "marks": 92, "base_marks": 92, "feasibility": "Hard"},
            {"name": "DAA", "credits": 4, "marks": 95, "base_marks": 95, "feasibility": "Hard"},
            {"name": "Computer Networks", "credits": 3, "marks": 90, "base_marks": 90, "feasibility": "Hard"},
            {"name": "Web Technology", "credits": 3, "marks": 86, "base_marks": 86, "feasibility": "Hard"},
        ],
    }
    student = _get_student()
    ctx = _shell_context(active, title)
    target = student.target_cgpa
    
    # Update scenarios based on target
    target_diff = target - student.current_cgpa
    factor = target_diff * 12
    for key in scenarios:
        for sub in scenarios[key]:
            sub["marks"] = max(40, min(100, round(sub["base_marks"] + factor)))

    ctx.update({
        "current_cgpa": student.current_cgpa,
        "target_cgpa": target,
        "required_avg": round(65 + factor),
        "scenarios_json": json.dumps(scenarios),
    })
    return ctx


def cgpa_planner(request):
    student = _get_student()
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_target = data.get("target_cgpa")
            if new_target is not None:
                student.target_cgpa = float(new_target)
                student.save()
                return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    ctx = _cgpa_planner_context("cgpa-planner", "CGPA Planner")
    return render(request, "pages/cgpa_planner.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 4 — DNA Profile
# ---------------------------------------------------------------------------

def dna_profile(request):
    sid = _get_student().student_id
    records = list(ResultRecord.objects.filter(student__student_id=sid).select_related("subject"))
    
    helix_subjects = []
    band_counts = {"strong": 0, "moderate": 0, "weak": 0, "critical": 0}

    if records:
        for r in records:
            score = r.final_score
            # Dynamic band assignment
            band = "critical" if score < 40 else "weak" if score < 55 else "moderate" if score < 75 else "strong"
            meta = _band_meta(band)
            helix_subjects.append({
                "name": r.subject.name,
                "marks": int(score),
                "max_marks": 100,
                "grade": r.pass_fail_status if hasattr(r, 'pass_fail_status') else ("P" if score >= 40 else "F"),
                "color": meta["color"],
                "band": band,
                "band_label": meta["label"]
            })
            band_counts[band] += 1
    else:
        # Fallback to demo data
        for s in DEFAULT_SUBJECTS:
            meta = _band_meta(s["band"])
            helix_subjects.append({**s, "color": meta["color"], "band_label": meta["label"]})
            band_counts[s["band"]] = band_counts.get(s["band"], 0) + 1

    ctx = _shell_context("dna-profile", "DNA Profile")
    ctx.update({
        "total_subjects": len(helix_subjects),
        "strong_count": band_counts["strong"],
        "moderate_count": band_counts["moderate"],
        "weak_count": band_counts["weak"],
        "critical_count": band_counts["critical"],
        "helix_subjects_json": json.dumps(helix_subjects),
        "subjects": helix_subjects,
        "distribution_json": json.dumps(band_counts),
    })
    return render(request, "pages/dna_profile.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 5 — Backlog Risk
# ---------------------------------------------------------------------------

def backlog_risk(request):
    risk_rows = [
        {"name": "Operating Systems", "current": 38, "level": "High", "trend": "Declining"},
        {"name": "Software Engineering", "current": 42, "level": "High", "trend": "Declining"},
        {"name": "Computer Networks", "current": 58, "level": "Medium", "trend": "Improving"},
        {"name": "Database Management", "current": 64, "level": "Medium", "trend": "Improving"},
        {"name": "Web Technology", "current": 78, "level": "Low", "trend": "Improving"},
        {"name": "Design & Analysis of Algorithms", "current": 71, "level": "Low", "trend": "Improving"},
    ]

    actions = [
        {"priority": 1, "title": "Recover Operating Systems", "desc": "Schedule daily 90-min revision focused on deadlocks and scheduling.",
         "subject": "Operating Systems", "effort": "1.5 hrs/day"},
        {"priority": 1, "title": "Re-attempt Software Engineering Lab", "desc": "Submit 2 pending lab reports and revise SDLC models.",
         "subject": "Software Engineering", "effort": "2 hrs/day"},
        {"priority": 2, "title": "Strengthen Computer Networks", "desc": "Practice subnetting + revise OSI model with weekend mocks.",
         "subject": "Computer Networks", "effort": "1 hr/day"},
        {"priority": 2, "title": "DBMS Query Practice", "desc": "Solve 10 SQL problems daily — focus on joins and normalization.",
         "subject": "DBMS", "effort": "45 mins/day"},
        {"priority": 3, "title": "Maintain Web Technology streak", "desc": "Continue mini-project, review React fundamentals weekly.",
         "subject": "Web Technology", "effort": "30 mins/day"},
    ]

    ctx = _shell_context("backlog-risk", "Backlog Risk")
    ctx.update({
        "at_risk": 4,
        "high_risk": 2,
        "actions_pending": 5,
        "risk_rows_json": json.dumps(risk_rows),
        "actions": actions,
    })
    return render(request, "pages/backlog_risk.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 6 — Emotional Health
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Wellness score helpers
# ---------------------------------------------------------------------------

# Colour map for mood labels (used both in Python and passed to the template)
_MOOD_COLOURS = {
    "calm":        "#22C55E",
    "focused":     "#22C55E",
    "hopeful":     "#22C55E",
    "stressed":    "#F59E0B",
    "anxious":     "#F97316",
    "sad":         "#EF4444",
    "overwhelmed": "#EF4444",
}
_MOOD_SCORE_DEFAULTS = {
    "calm": 0.6, "focused": 0.5, "hopeful": 0.7,
    "stressed": -0.5, "anxious": -0.6,
    "sad": -0.7, "overwhelmed": -0.8,
}


def _compute_wellness_score(student_id):
    """
    Returns (score_int, label_str, mood_trail_list).

    score_int  – 0-100 wellness score computed from the last 14 days of
                 tagged user messages (weighted so today counts more).
    label_str  – human label: Excellent / Good / Fair / Low.
    mood_trail – list of 14 dicts {date_str, label, colour, score}
                 ordered oldest-first; days with no data use empty label.
    """
    from datetime import date, timedelta
    from django.utils import timezone

    today = timezone.localdate()
    cutoff = today - timedelta(days=13)  # 14 days including today

    tagged = list(
        WellnessChatMessage.objects
        .filter(
            student_id=student_id,
            role="user",
            mood_score__isnull=False,
            created_at__date__gte=cutoff,
        )
        .values("mood_score", "mood_label", "created_at")
        .order_by("created_at")
    )

    # Need at least 3 tagged messages before we override the default
    if len(tagged) < 3:
        return 72, "Good", []

    # Group by date → mean score + dominant label per day
    from collections import defaultdict
    day_scores = defaultdict(list)
    day_labels = defaultdict(list)
    for m in tagged:
        d = m["created_at"].date() if hasattr(m["created_at"], "date") else m["created_at"]
        if hasattr(d, 'date'):
            d = d.date()
        day_scores[d].append(m["mood_score"])
        if m["mood_label"]:
            day_labels[d].append(m["mood_label"])

    # Weighted sum — day 0 (oldest in window) weight 0.3 → day 13 (today) weight 1.0
    total_weight = 0.0
    weighted_sum = 0.0
    for i in range(14):
        d = cutoff + timedelta(days=i)
        if d not in day_scores:
            continue
        weight = 0.3 + 0.7 * (i / 13)  # linear 0.3 → 1.0
        mean_s = sum(day_scores[d]) / len(day_scores[d])
        weighted_sum += mean_s * weight
        total_weight += weight

    raw = weighted_sum / total_weight if total_weight else 0.0  # -1 to +1
    score_int = int(round(50 + raw * 50))                       # map to 0-100
    score_int = max(0, min(100, score_int))

    if score_int >= 80:
        label = "Excellent"
    elif score_int >= 60:
        label = "Good"
    elif score_int >= 40:
        label = "Fair"
    else:
        label = "Low"

    # Build 14-day trail (oldest first)
    trail = []
    for i in range(14):
        d = cutoff + timedelta(days=i)
        if d in day_scores:
            mean_s = sum(day_scores[d]) / len(day_scores[d])
            # pick most-frequent label for the day
            from collections import Counter
            dominant = Counter(day_labels.get(d, [])).most_common(1)
            lbl = dominant[0][0] if dominant else ""
            trail.append({
                "date": d.strftime("%b %d"),
                "label": lbl.capitalize() if lbl else "",
                "colour": _MOOD_COLOURS.get(lbl, "#6B7280"),
                "score": round(mean_s, 2),
            })
        else:
            trail.append({"date": d.strftime("%b %d"), "label": "", "colour": "#E5E7EB", "score": None})

    return score_int, label, trail


# ---------------------------------------------------------------------------
# PAGE 6 — Emotional Health
# ---------------------------------------------------------------------------

def emotional_health(request):
    ctx = _shell_context("emotional-health", "Emotional Health")
    saved = list(
        WellnessChatMessage.objects
        .filter(student_id=_get_student().student_id)
        .order_by("created_at")
        .values("role", "content", "created_at")
    )
    chat_history = [
        {
            "role": m["role"],
            "content": m["content"],
            "time": m["created_at"].strftime("%b %d, %I:%M %p"),
        }
        for m in saved
    ]
    wellness_score, wellness_label, mood_trail = _compute_wellness_score(
        _get_student().student_id
    )
    ctx.update({
        "wellness_score": wellness_score,
        "wellness_label": wellness_label,
        "mood_trail_json": json.dumps(mood_trail),
        "chat_history": chat_history,
        "chat_history_json": json.dumps([
            {"role": m["role"], "content": m["content"]} for m in chat_history
        ]),
        "radar_json": json.dumps({
            "labels": ["Study", "Sleep", "Phone", "Gaming", "Social Media", "Stress"],
            "values": [7, 6, 8, 3, 5, 4],
        }),
        "tips": [
            {"title": "Wind down at 10 pm", "desc": "Reduce screen time 1 hr before bed for deeper sleep.",
             "impact": "+8% performance", "color": "#6C3CE1"},
            {"title": "Pomodoro study blocks", "desc": "25 min focus / 5 min break improves retention.",
             "impact": "+12% performance", "color": "#22C55E"},
            {"title": "Limit Instagram to 30 min/day", "desc": "Frees ~1.5 hrs daily for revision.",
             "impact": "+6% performance", "color": "#3B82F6"},
            {"title": "Daily 10 min meditation", "desc": "Lower stress and improve concentration.",
             "impact": "+5% performance", "color": "#F59E0B"},
            {"title": "Walk after meals", "desc": "Boosts focus during evening study sessions.",
             "impact": "+3% performance", "color": "#22C55E"},
        ],
        "insights": [
            {"text": "High screen time (4h) is reducing retention in theory subjects.", "color": "#EF4444"},
            {"text": "Sleep below 6 hrs correlates with backlog risk in OS & SE.", "color": "#F59E0B"},
            {"text": "Consistent morning study window improves Web Tech scores.", "color": "#22C55E"},
        ],
    })
    return render(request, "pages/emotional_health.html", ctx)


@require_POST
def emotional_chat(request):
    """AI wellness assistant: detects student's problem and suggests solutions."""
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if payload.get("clear"):
        WellnessChatMessage.objects.filter(student_id=_get_student().student_id).delete()
        return JsonResponse({"cleared": True})

    user_message = (payload.get("message") or "").strip()
    history = payload.get("history") or []

    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    if _openai_client is None:
        # ---- Demo Mode Fallback ----
        # If no key is configured, provide a realistic mock response based on keywords
        msg = user_message.lower()
        if "exam" in msg or "anxious" in msg or "test" in msg:
            reply = "I hear you — exam anxiety is very real, especially when you're aiming for a high CGPA. It sounds like the pressure to perform is getting a bit overwhelming. This usually happens when we look at the whole syllabus at once instead of one chapter. Try this: (1) Break your study plan into 2-hour blocks, (2) focus only on the next 1 topic, and (3) take a 10-minute walk without your phone. You've got this!"
            mood = {"score": -0.6, "label": "anxious"}
        elif "sleep" in msg or "night" in msg or "tired" in msg:
            reply = "It sounds like your sleep cycle is a bit out of sync, which is likely making everything else feel harder. The underlying cause is often 'revenge bedtime procrastination' where we scroll to feel in control of our time. Try this: (1) Set a 'digital sunset' at 11 PM, (2) keep your phone out of arm's reach, and (3) try a 5-minute breathing exercise before lying down. Consistency is key here."
            mood = {"score": -0.5, "label": "stressed"}
        elif "motivation" in msg or "bored" in msg or "lazy" in msg:
            reply = "I understand — it's hard to stay driven when the finish line feels so far away. This 'no motivation' phase usually comes from burnout or a lack of small wins. Try this: (1) Do the smallest task on your list first (even just 5 mins), (2) change your study environment today, and (3) reward yourself with something you enjoy after finishing one topic. Small steps lead to big momentum."
            mood = {"score": -0.4, "label": "sad"}
        elif "focus" in msg or "concentrate" in msg or "distract" in msg:
            reply = "It's tough when your mind keeps drifting — focus is like a muscle that gets tired. The likely cause is 'context switching' from frequent phone notifications. Try this: (1) Use the Pomodoro technique (25m work / 5m break), (2) use a site blocker for social media during study hours, and (3) clear your desk of everything except what you're studying right now. Your brain will thank you."
            mood = {"score": -0.5, "label": "stressed"}
        else:
            reply = "Thank you for sharing that with me. It sounds like you're carrying a lot on your plate right now. This usually stems from trying to balance academic rigor with personal well-being. Try this: (1) List your top 3 stressors on paper, (2) reach out to one friend for a quick chat, and (3) give yourself permission to rest for 30 minutes today. I'm here to support you."
            mood = {"score": -0.3, "label": "overwhelmed"}

        # Persist turns in demo mode
        sid = _get_student().student_id
        WellnessChatMessage.objects.create(
            student_id=sid, role="user", content=user_message,
            mood_score=mood["score"], mood_label=mood["label"]
        )
        saved = WellnessChatMessage.objects.create(student_id=sid, role="assistant", content=reply)
        return JsonResponse({
            "reply": reply,
            "time": saved.created_at.strftime("%b %d, %I:%M %p"),
            "mood": mood,
            "demo": True
        })

    student = _get_student()
    system_prompt = (
        f"You are GradeDNA AI Wellness Coach — a kind, evidence-based assistant for "
        f"{student.name}, a {student.course} student in semester "
        f"{student.semester}. The student may share academic stress, sleep, "
        "focus, motivation, anxiety, exam pressure, time-management or relationship "
        "struggles. Your job: (1) briefly mirror back what you understand the core "
        "problem to be, (2) name the likely underlying cause in 1 line, (3) give 3 "
        "specific, doable steps the student can try this week. Use a warm, supportive "
        "tone — never clinical, never preachy. Keep the whole reply under 180 words. "
        "Use plain text with short paragraphs. If the student mentions self-harm or "
        "crisis, gently encourage them to reach out to a trusted adult, counsellor, "
        "or the iCall helpline (9152987821 in India). "
        "After your advice, on a brand-new line append exactly: "
        'MOOD: {"score": <float between -1.0 and 1.0>, "label": "<one of: calm, focused, stressed, anxious, sad, overwhelmed, hopeful>"}'
        " where score reflects the emotional tone of the student's message "
        "(not the reply). Do NOT include that line anywhere else in your answer."
    )

    messages_payload = [{"role": "system", "content": system_prompt}]
    for turn in history[-8:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages_payload.append({"role": role, "content": content})
    messages_payload.append({"role": "user", "content": user_message})

    try:
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = _openai_client.chat.completions.create(
            model="gpt-5",
            messages=messages_payload,
            max_completion_tokens=8192,
        )
        raw_reply = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        return JsonResponse({"error": f"AI request failed: {exc}"}, status=502)

    # ---- Strip and parse the MOOD: tag ----
    mood_score_val = None
    mood_label_val = ""
    reply_lines = raw_reply.splitlines()
    clean_lines = []
    for line in reply_lines:
        stripped = line.strip()
        if stripped.startswith("MOOD:"):
            try:
                mood_data = json.loads(stripped[len("MOOD:"):].strip())
                mood_score_val = float(mood_data.get("score", 0.0))
                mood_score_val = max(-1.0, min(1.0, mood_score_val))
                raw_label = str(mood_data.get("label", "")).lower().strip()
                valid_labels = {"calm", "focused", "stressed", "anxious", "sad", "overwhelmed", "hopeful"}
                mood_label_val = raw_label if raw_label in valid_labels else ""
            except (json.JSONDecodeError, ValueError):
                pass  # tag malformed — silently ignore
        else:
            clean_lines.append(line)
    reply = "\n".join(clean_lines).strip()

    # Persist both turns; tag the user message with the detected mood
    sid = _get_student().student_id
    WellnessChatMessage.objects.create(
        student_id=sid,
        role="user",
        content=user_message,
        mood_score=mood_score_val,
        mood_label=mood_label_val,
    )
    saved = WellnessChatMessage.objects.create(student_id=sid, role="assistant", content=reply)

    return JsonResponse({
        "reply": reply,
        "time": saved.created_at.strftime("%b %d, %I:%M %p"),
        "mood": {"score": mood_score_val, "label": mood_label_val},
    })


def emotional_chat_pdf(request):
    """Export wellness chat history as a downloadable PDF."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.lib.enums import TA_LEFT
    from html import escape as _esc

    sid = _get_student().student_id
    msgs = list(
        WellnessChatMessage.objects.filter(student_id=sid).order_by("created_at")
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Wellness Chat Export — GradeDNA AI",
    )

    styles = getSampleStyleSheet()
    h_title = ParagraphStyle(
        "h_title", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=22, textColor=HexColor("#6C3CE1"), spaceAfter=4,
    )
    h_sub = ParagraphStyle(
        "h_sub", parent=styles["Normal"], fontSize=10,
        textColor=HexColor("#6B7280"), spaceAfter=14,
    )
    bubble_user = ParagraphStyle(
        "bubble_user", parent=styles["Normal"], fontSize=10.5, leading=15,
        textColor=HexColor("#FFFFFF"), alignment=TA_LEFT,
        leftIndent=4, rightIndent=4,
    )
    bubble_ai = ParagraphStyle(
        "bubble_ai", parent=styles["Normal"], fontSize=10.5, leading=15,
        textColor=HexColor("#1A1A2E"), alignment=TA_LEFT,
        leftIndent=4, rightIndent=4,
    )
    timestamp = ParagraphStyle(
        "timestamp", parent=styles["Normal"], fontSize=8,
        textColor=HexColor("#9CA3AF"), spaceBefore=2, spaceAfter=10,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"], fontSize=9,
        textColor=HexColor("#6B7280"), spaceBefore=8, spaceAfter=2,
    )

    student = _get_student()
    story = [
        Paragraph("GradeDNA AI · Wellness Chat Log", h_title),
        Paragraph(
            f"{student.name} · {student.course} · "
            f"Semester {student.semester} · ID {sid}",
            h_sub,
        ),
    ]

    if not msgs:
        story.append(Paragraph(
            "No conversations yet. Open the Emotional Health page and "
            "share what's on your mind to start chatting with the wellness coach.",
            styles["Italic"],
        ))
    else:
        for m in msgs:
            who = "You" if m.role == "user" else "Wellness Coach"
            ts = m.created_at.strftime("%b %d, %Y · %I:%M %p")
            story.append(Paragraph(f"<b>{who}</b> &nbsp; · &nbsp; {ts}", label_style))

            text_html = _esc(m.content).replace("\n", "<br/>")
            if m.role == "user":
                bubble = Paragraph(text_html, bubble_user)
                bg = HexColor("#6C3CE1")
            else:
                bubble = Paragraph(text_html, bubble_ai)
                bg = HexColor("#F4F6FA")

            tbl = Table([[bubble]], colWidths=[170 * mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ROUNDEDCORNERS", [10, 10, 10, 10]),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "<i>Exported from GradeDNA AI · For personal reference only · "
        "Not a substitute for professional mental health support.</i>",
        ParagraphStyle("foot", parent=styles["Normal"], fontSize=8,
                       textColor=HexColor("#9CA3AF")),
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    filename = f"wellness_chat_{sid}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# PAGE 7 — Performance
# ---------------------------------------------------------------------------

def performance(request):
    rows = [
        {"name": "DBMS", "you": 78, "avg": 69.8, "delta": 8.2, "sigma": 0.8, "rank": 6, "band": "Above Avg"},
        {"name": "Operating Systems", "you": 52, "avg": 57.1, "delta": -5.1, "sigma": -0.6, "rank": 38, "band": "Below Avg"},
        {"name": "DAA", "you": 71, "avg": 67.4, "delta": 3.6, "sigma": 0.4, "rank": 14, "band": "Average"},
        {"name": "Computer Networks", "you": 64, "avg": 65.0, "delta": -1.0, "sigma": -0.1, "rank": 22, "band": "Average"},
        {"name": "Web Technology", "you": 82, "avg": 70.5, "delta": 11.5, "sigma": 1.2, "rank": 3, "band": "Excellent"},
        {"name": "Software Engineering", "you": 38, "avg": 55.2, "delta": -17.2, "sigma": -1.6, "rank": 47, "band": "At Risk"},
    ]

    ctx = _shell_context("performance", "Performance")
    ctx.update({
        "rank": 12,
        "percentile": 84,
        "delta": 4.1,
        "band": "Above Average",
        "rows": rows,
        "rows_json": json.dumps(rows),
    })
    return render(request, "pages/performance.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 9 — Reports
# ---------------------------------------------------------------------------

def reports(request):
    ctx = _shell_context("reports", "Reports")
    ctx.update({
        "preview_data": request.session.get("csv_preview_data"),
        "has_errors": request.session.get("csv_has_errors", False),
        "save_summary": request.session.pop("csv_save_summary", None),
    })
    return render(request, "pages/reports.html", ctx)


# ---------------------------------------------------------------------------
# PAGE 10 — Settings
# ---------------------------------------------------------------------------

def settings_page(request):
    student = _get_student()
    
    if request.method == 'POST':
        # Update student profile
        student.name = request.POST.get('name', student.name)
        student.email = request.POST.get('email', student.email)
        student.phone = request.POST.get('phone', student.phone)
        student.department = request.POST.get('department', student.department)
        student.course = request.POST.get('course', student.course)
        
        # New: Current CGPA
        ccgpa = request.POST.get('current_cgpa')
        if ccgpa:
            try:
                student.current_cgpa = float(ccgpa)
            except ValueError:
                pass

        student.save()
        messages.success(request, "Account settings updated successfully!")
        return redirect('settings_page')

    ctx = _shell_context("settings", "Settings")
    
    # Parse mood counts from the reference CSV for the Datasets tab
    dataset_counts = {}
    try:
        csv_path = os.path.join(settings.BASE_DIR, "static", "data", "student_wellness_reference.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                from collections import Counter
                moods = [row["mood"] for row in reader if row.get("mood")]
                dataset_counts = dict(Counter(moods))
    except Exception:
        pass

    ctx.update({
        "dataset_counts": dataset_counts
    })
    return render(request, "pages/settings.html", ctx)


# ---------------------------------------------------------------------------
# CSV Upload (used inside the Reports page flow)
# ---------------------------------------------------------------------------

def upload_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Please upload a valid CSV file.")
            return redirect("reports")

        try:
            file_data = csv_file.read().decode("utf-8-sig")
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)
            reader.fieldnames = [name.strip() for name in reader.fieldnames if name]

            required_cols = [
                "student_id", "student_name", "department", "semester",
                "subject_code", "subject_name", "credits",
                "internal_marks", "external_marks",
                "attendance_percentage", "assignment_score",
            ]
            missing_cols = [c for c in required_cols if c not in reader.fieldnames]
            if missing_cols:
                messages.error(
                    request,
                    f"Missing columns: {', '.join(missing_cols)}. Found: {reader.fieldnames}",
                )
                return redirect("reports")

            preview_data = []
            has_errors = False
            for row in reader:
                row_data = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                row_data["is_valid"] = True
                row_data["errors"] = []

                if not row_data.get("student_id"):
                    row_data["is_valid"] = False
                    row_data["errors"].append("Missing Student ID")

                try:
                    internal = float(row_data.get("internal_marks", 0) or 0)
                    row_data["internal_marks"] = internal
                    if internal < 0 or internal > 40:
                        row_data["is_valid"] = False
                        row_data["errors"].append("Invalid Internal Marks (0-40)")
                except ValueError:
                    row_data["is_valid"] = False
                    row_data["errors"].append("Internal Marks must be a number")
                    internal = 0

                try:
                    external = float(row_data.get("external_marks", 0) or 0)
                    row_data["external_marks"] = external
                    if external < 0 or external > 60:
                        row_data["is_valid"] = False
                        row_data["errors"].append("Invalid External Marks (0-60)")
                except ValueError:
                    row_data["is_valid"] = False
                    row_data["errors"].append("External Marks must be a number")
                    external = 0

                try:
                    attendance = float(row_data.get("attendance_percentage", 0) or 0)
                    row_data["attendance_percentage"] = attendance
                    if attendance < 0 or attendance > 100:
                        row_data["is_valid"] = False
                        row_data["errors"].append("Invalid Attendance %")
                except ValueError:
                    row_data["is_valid"] = False
                    row_data["errors"].append("Attendance must be a number")

                final_score = (internal or 0) + (external or 0)
                row_data["calculated_final_score"] = final_score
                row_data["calculated_status"] = "PASS" if final_score >= 40 else "FAIL"

                if not row_data["is_valid"]:
                    has_errors = True
                preview_data.append(row_data)

            request.session["csv_preview_data"] = preview_data
            request.session["csv_has_errors"] = has_errors
            return redirect("reports")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect("reports")

    return redirect("reports")


def confirm_csv_upload(request):
    if request.method == "POST":
        preview_data = request.session.get("csv_preview_data")
        if not preview_data:
            messages.error(request, "No data to save. Please upload again.")
            return redirect("reports")

        valid_rows = [r for r in preview_data if r["is_valid"]]
        students_dict, subjects_dict = {}, {}

        for row in valid_rows:
            student_id = str(row["student_id"])
            if student_id not in students_dict:
                student, _ = Student.objects.get_or_create(
                    student_id=student_id,
                    defaults={
                        "name": row.get("student_name", "Unknown"),
                        "department": row.get("department", "Unknown"),
                        "semester": int(row.get("semester", 1)),
                    },
                )
                students_dict[student_id] = student
            else:
                student = students_dict[student_id]

            subject_code = str(row["subject_code"])
            if subject_code not in subjects_dict:
                subject, _ = Subject.objects.get_or_create(
                    code=subject_code,
                    defaults={
                        "name": row.get("subject_name", "Unknown"),
                        "credits": int(row.get("credits", 3)),
                        "semester": int(row.get("semester", 1)),
                    },
                )
                subjects_dict[subject_code] = subject
            else:
                subject = subjects_dict[subject_code]

            ResultRecord.objects.update_or_create(
                student=student,
                subject=subject,
                defaults={
                    "internal_marks": float(row.get("internal_marks", 0)),
                    "external_marks": float(row.get("external_marks", 0)),
                    "attendance_percentage": float(row.get("attendance_percentage", 0)),
                    "assignment_score": float(row.get("assignment_score", 0)),
                    "final_score": float(row.get("calculated_final_score", 0)),
                    "pass_fail_status": row.get("calculated_status", "FAIL"),
                },
            )

        request.session["csv_save_summary"] = {
            "saved": len(valid_rows),
            "failed": len(preview_data) - len(valid_rows),
        }
        del request.session["csv_preview_data"]
        if "csv_has_errors" in request.session:
            del request.session["csv_has_errors"]
        messages.success(request, f"Successfully imported {len(valid_rows)} records.")
        return redirect("reports")

    return redirect("reports")


def download_report(request):
    student = _get_student()
    context = {
        "student_name": student.name,
        "student_id": student.student_id,
        "pass_percentage": 82,
        "fail_percentage": 18,
        "high_risk_subjects": ["Operating Systems", "Software Engineering"],
        "overall_cgpa": 7.24,
    }
    return render(request, "report_template.html", context)
