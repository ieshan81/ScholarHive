"""Demo seed data for local development — clearly labeled."""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.profile import Profile
from app.models.story import Story
from app.models.scholarship import Scholarship
from app.models.essay import Essay
from app.models.missing_info import MissingInfoRequest
from app.models.document import Document


def seed_database(db: Session) -> None:
    if db.query(Scholarship).filter(Scholarship.is_demo == True).first():  # noqa: E712
        return

    if not db.query(Profile).filter(Profile.id == 1).first():
        db.add(Profile(
            id=1,
            university="Sample University",
            major="Mechanical Engineering",
            international_student=True,
            visa_status="F-1",
            gpa=3.6,
            career_goals="Automotive and sustainable energy systems",
            personal_details="International student from South Asia",
        ))

    stories = [
        Story(
            title="FSAE Brake System Redesign",
            category="engineering project",
            tags="FSAE,mechanical,leadership",
            summary="Led brake subsystem redesign under tight budget.",
            full_story="During FSAE season I coordinated caliper selection and validation testing.",
            verified_by_user=True,
            is_demo=True,
        ),
        Story(
            title="Family Support During Tuition Gap",
            category="financial challenge",
            tags="family,international",
            summary="Managed semester costs while supporting family abroad.",
            full_story="I balanced part-time work with engineering coursework when exchange rates shifted.",
            verified_by_user=False,
            is_demo=True,
        ),
    ]
    for s in stories:
        db.add(s)

    scholarships = [
        Scholarship(
            name="[DEMO] ASME Mechanical Engineering Scholarship",
            source_url="https://example.com/asme-demo",
            source_type="demo",
            award_amount="$5,000",
            deadline=date.today() + timedelta(days=45),
            essay_required=True,
            essay_prompt="Describe an engineering project and your career goals.",
            word_limit=500,
            major_requirement="Mechanical Engineering",
            international_allowed="yes",
            trust_score=85,
            effort_score=55,
            eligibility_score=72,
            status="eligible",
            next_action="Generate essay draft",
            is_demo=True,
        ),
        Scholarship(
            name="[DEMO] International Student STEM Grant",
            source_url="https://example.com/intl-demo",
            source_type="demo",
            award_amount="$2,500",
            deadline=date.today() + timedelta(days=20),
            essay_required=False,
            major_requirement="STEM",
            international_allowed="yes",
            trust_score=70,
            effort_score=30,
            eligibility_score=80,
            status="ready_to_apply",
            next_action="Prepare application package",
            is_demo=True,
        ),
        Scholarship(
            name="[DEMO] Citizens-Only Merit Award",
            source_url="https://example.com/citizen-demo",
            source_type="demo",
            award_amount="$10,000",
            deadline=date.today() + timedelta(days=60),
            citizenship_requirement="U.S. Citizen only",
            international_allowed="no",
            essay_required=True,
            trust_score=60,
            effort_score=70,
            eligibility_score=5,
            status="not_eligible",
            next_action="Skip — citizenship requirement",
            is_demo=True,
        ),
    ]
    for sch in scholarships:
        db.add(sch)
    db.flush()

    db.add(Essay(
        scholarship_id=1,
        prompt="Describe an engineering project and your career goals.",
        draft_text="[DEMO DRAFT] Working on FSAE taught me to translate theory into reliable hardware...",
        status="needs_review",
        word_count=120,
        authenticity_score=65,
        is_demo=True,
    ))

    db.add(MissingInfoRequest(
        scholarship_id=1,
        question="[DEMO] Please share 3–5 lines about a verified financial challenge story.",
        reason="Essay may need financial hardship context — no verified story in Story Bank",
        status="pending",
        is_demo=True,
    ))
    db.add(MissingInfoRequest(
        question="[DEMO] What is your expected graduation year?",
        reason="Profile missing graduation year for eligibility checks",
        status="pending",
        is_demo=True,
    ))

    db.add(Document(file_name="resume_demo.pdf", file_type="resume", status="missing", is_demo=True))
    db.add(Document(file_name="transcript_demo.pdf", file_type="transcript", status="uploaded", is_demo=True))

    db.commit()
