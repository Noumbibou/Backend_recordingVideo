import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

# ⚡ Variables globales
EMAIL = "william@gmail.com"
PASSWORD = "fnrw0204"
TOKEN = None


def auth_login():
    url = f"{BASE_URL}/auth/login/"
    payload = {
        "email": "william@gmail.com",
        "password": "fnrw0204"
    }
    r = requests.post(url, json=payload)
    print("🔑 Status code:", r.status_code)
    print("🔑 Response headers:", r.headers)
    try:
        print("🔑 Response JSON:", r.json())
    except Exception:
        print("🔑 Response raw text:", r.text)


def headers(auth=True):
    """Headers avec ou sans token"""
    h = {"Content-Type": "application/json"}
    if auth and TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def create_hiring_manager():
    url = f"{BASE_URL}/api/hiring-managers/"
    data = {"company_name": "TestCorp", "position": "CTO"}
    r = requests.post(url, json=data, headers=headers())
    print("👔 HiringManager:", r.status_code, r.json())
    return r.json()


def create_candidate():
    url = f"{BASE_URL}/api/candidates/"
    data = {"email": "candidate@test.com", "full_name": "John Doe"}
    r = requests.post(url, json=data, headers=headers())
    print("🙍 Candidate:", r.status_code, r.json())
    return r.json()


def create_campaign():
    url = f"{BASE_URL}/api/campaigns/"
    data = {
        "title": "Test Campaign",
        "description": "Backend test campaign",
        "deadline": "2025-12-31T23:59:59Z"
    }
    r = requests.post(url, json=data, headers=headers())
    print("📢 Campaign:", r.status_code, r.json())
    return r.json()


def create_question(campaign_id):
    url = f"{BASE_URL}/api/questions/"
    data = {
        "campaign": campaign_id,
        "text": "Présentez-vous en 1 minute",
        "time_limit": 60
    }
    r = requests.post(url, json=data, headers=headers())
    print("❓ Question:", r.status_code, r.json())
    return r.json()


def create_session(candidate_id, campaign_id):
    url = f"{BASE_URL}/api/sessions/"
    data = {"candidate": candidate_id, "campaign": campaign_id}
    r = requests.post(url, json=data, headers=headers())
    print("🎥 Session:", r.status_code, r.json())
    return r.json()


def upload_response_file(session_id, question_id):
    url = f"{BASE_URL}/api/responses/"
    data = {
        "session": session_id,
        "question": question_id,
        "duration": 42,
        "preparation_time_used": 10,
        "response_time_used": 32
    }
    file_path = Path("sample.mp4")
    if not file_path.exists():
        print("⚠️ sample.mp4 introuvable, skip upload fichier")
        return None

    files = {"video_file": open(file_path, "rb")}
    r = requests.post(url, data=data, files=files, headers={"Authorization": f"Bearer {TOKEN}"})
    print("📹 Response (file):", r.status_code, r.json())
    return r.json()


def upload_response_url(session_id, question_id):
    url = f"{BASE_URL}/api/responses/"
    data = {
        "session": session_id,
        "question": question_id,
        "duration": 45,
        "preparation_time_used": 12,
        "response_time_used": 33,
        "video_url": "http://example.com/video.mp4"
    }
    r = requests.post(url, json=data, headers=headers())
    print("🌐 Response (url):", r.status_code, r.json())
    return r.json()


def list_candidate_sessions(candidate_id):
    url = f"{BASE_URL}/api/candidates/{candidate_id}/"
    r = requests.get(url, headers=headers())
    print("📂 Candidate Sessions:", r.status_code, r.json())


def list_logs():
    url = f"{BASE_URL}/api/logs/"
    r = requests.get(url, headers=headers())
    print("📝 Logs:", r.status_code, r.json())


def list_ai_analysis():
    url = f"{BASE_URL}/api/ai-analysis/"
    r = requests.get(url, headers=headers())
    print("🤖 AI Analysis:", r.status_code, r.json())


if __name__ == "__main__":
    # 1. Auth
    auth_login()

    # 2. Hiring Manager
    hm = create_hiring_manager()

    # 3. Candidate
    candidate = create_candidate()

    # 4. Campaign
    campaign = create_campaign()

    # 5. Question
    question = create_question(campaign["id"])

    # 6. Session
    session = create_session(candidate["id"], campaign["id"])

    # 7. Upload responses
    upload_response_file(session["id"], question["id"])
    upload_response_url(session["id"], question["id"])

    # 8. Listing
    list_candidate_sessions(candidate["id"])
    list_logs()
    list_ai_analysis()
