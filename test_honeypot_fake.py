from src.honeypot import compute_honeypot_penalty

# Fake candidate that is obviously a honeypot
fake_honeypot = {
    "candidate_id": "CAND_FAKE001",
    "profile": {
        "current_title": "HR Manager",
        "current_company": "Dunder Mifflin",
        "years_of_experience": 15,  # claims 15 years
    },
    "career_history": [
        {
            "company": "Dunder Mifflin",
            "title": "HR Manager",
            "start_date": "2024-01-01",
            "end_date": None,
            "duration_months": 6,   # only 6 months total — gap of 14.5 years!
            "is_current": True,
            "industry": "Paper Products",
            "company_size": "201-500",
            "description": "Managed HR operations."
        }
    ],
    "education": [],
    "skills": [
        {"name": "Python", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "RAG", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "FAISS", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "LLM", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "Embeddings", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "Pinecone", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
        {"name": "Transformers", "proficiency": "expert", "endorsements": 0, "duration_months": 60},
    ],
    "certifications": [],
    "languages": [],
    "redrob_signals": {
        "profile_completeness_score": 99,
        "last_active_date": "2026-06-01",
        "open_to_work_flag": True,
        "connection_count": 500,
        "endorsements_received": 0,   # 500 connections but 0 endorsements
        "offer_acceptance_rate": 1.0,
        "interview_completion_rate": 0.0,  # accepted all offers but never interviewed
        "github_activity_score": -1,
        "skill_assessment_scores": {},
        "profile_views_received_30d": 0,
        "applications_submitted_30d": 0,
        "recruiter_response_rate": 0,
        "avg_response_time_hours": 0,
        "notice_period_days": 0,
        "expected_salary_range_inr_lpa": {"min": 0, "max": 0},
        "preferred_work_mode": "remote",
        "willing_to_relocate": False,
        "search_appearance_30d": 0,
        "saved_by_recruiters_30d": 0,
        "verified_email": False,
        "verified_phone": False,
        "linkedin_connected": False,
        "signup_date": "2024-01-01",
    }
}

penalty, reason = compute_honeypot_penalty(fake_honeypot)
print(f"Penalty: {penalty}")
print(f"Reason:  {reason}")
print()
if penalty == 0.0:
    print("FATAL honeypot correctly detected!")
elif penalty < 1.0:
    print(f"Honeypot partially detected (penalty={penalty})")
else:
    print("WARNING: honeypot not detected")