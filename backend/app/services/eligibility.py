"""Eligibility engine — scores scholarships against profile without guessing."""
from datetime import date
from app.models.profile import Profile
from app.models.scholarship import Scholarship


def _contains(text: str | None, *terms: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(t.lower() in lower for t in terms)


def _recommended_action(status: str, scholarship: Scholarship) -> str:
    if scholarship.manual_step_likely or scholarship.status == "manual_step_needed":
        return "Complete manual portal steps (login/CAPTCHA/signature may be required)"
    if status == "not_eligible":
        return "Skip or archive"
    if status == "missing_info":
        return "Answer missing info questions in Telegram or Profile Vault"
    if scholarship.essay_required and status in ("eligible", "maybe_eligible"):
        return "Draft essay in Essay Studio → Personal Voice Review → approve"
    if status == "eligible":
        return "Prepare application package for human review"
    return "Verify eligibility on official source"


def evaluate_eligibility(profile: Profile | None, scholarship: Scholarship) -> dict:
    reasons: list[str] = []
    blockers: list[str] = []
    missing: list[str] = []
    score = 45.0

    if scholarship.deadline and scholarship.deadline < date.today():
        blockers.append("Deadline has passed")
        return {
            "eligibility_score": 0.0,
            "status_recommendation": "not_eligible",
            "reasons": reasons,
            "blockers": blockers,
            "missing_information": missing,
            "recommended_next_action": "Skip — deadline passed",
            "effort_score": scholarship.effort_score,
            "priority_score": 0.0,
        }

    if not profile:
        missing.append("Profile not configured — complete Profile Vault")
        return {
            "eligibility_score": 20.0,
            "status_recommendation": "missing_info",
            "reasons": reasons,
            "blockers": blockers,
            "missing_information": missing,
            "recommended_next_action": _recommended_action("missing_info", scholarship),
            "effort_score": scholarship.effort_score,
            "priority_score": 10.0,
        }

    # International / citizenship
    intl = (scholarship.international_allowed or "unknown").lower()
    if intl == "no" and profile.international_student:
        blockers.append("International students not eligible per listing")
        score -= 45
    elif intl == "yes" and profile.international_student:
        reasons.append("International students explicitly allowed")
        score += 18
    elif intl == "unknown" and profile.international_student:
        missing.append("Confirm international student eligibility on official portal")
        score -= 8

    if scholarship.citizenship_requirement:
        if _contains(scholarship.citizenship_requirement, "us citizen", "u.s. citizen", "citizen only") and profile.international_student:
            blockers.append(f"Citizenship restriction: {scholarship.citizenship_requirement}")
            score -= 40
        elif profile.international_student and not profile.visa_status:
            missing.append("Add visa status to profile for citizenship checks")

    # Major / mechanical engineering
    if scholarship.major_requirement:
        req = scholarship.major_requirement.lower()
        if profile.major:
            if _contains(req, "mechanical", "engineering", "stem"):
                if _contains(profile.major, "mechanical", "engineering"):
                    reasons.append("Strong match: Mechanical Engineering / STEM")
                    score += 20
                else:
                    missing.append(f"Verify STEM/mechanical fit: {scholarship.major_requirement}")
                    score -= 5
            else:
                missing.append(f"Verify major requirement: {scholarship.major_requirement}")
        else:
            missing.append("Set your major in Profile Vault")
    elif _contains(scholarship.name, "mechanical", "engineering"):
        reasons.append("Engineering-related opportunity title")
        score += 8

    # Degree level
    if scholarship.education_level_requirement:
        if not profile.education:
            missing.append(f"Confirm education level: {scholarship.education_level_requirement}")
        elif _contains(profile.education, "undergraduate", "bachelor") and _contains(
            scholarship.education_level_requirement, "undergraduate", "bachelor"
        ):
            reasons.append("Undergraduate level appears compatible")
            score += 10

    # GPA
    if scholarship.gpa_requirement or (scholarship.eligibility_notes and "gpa" in scholarship.eligibility_notes.lower()):
        if profile.gpa is None:
            missing.append("GPA requirement mentioned — add GPA to profile")
        else:
            reasons.append(f"GPA on file: {profile.gpa}")
            score += 8

    # Location / university
    if profile.university and scholarship.eligibility_notes:
        if profile.university.lower() in scholarship.eligibility_notes.lower():
            reasons.append("University referenced in eligibility notes")
            score += 5

    # Essay / documents / effort
    if scholarship.essay_required:
        reasons.append("Essay required — budget time in Essay Studio")
        scholarship.effort_score = max(scholarship.effort_score, 55.0)
    else:
        scholarship.effort_score = min(scholarship.effort_score, 45.0)

    if scholarship.required_documents and not scholarship.required_documents.strip():
        missing.append("Required documents unclear — verify on application portal")

    # Portal / manual steps
    if scholarship.portal_login_required == "yes" or scholarship.manual_step_likely:
        reasons.append("Application portal likely requires manual steps")
        missing.append("Expect login/CAPTCHA/signature — mark Manual Step Needed when preparing")
        scholarship.manual_step_likely = True

    # Trust from web discovery
    if scholarship.trust_score < 40:
        missing.append(f"Low trust score ({scholarship.trust_score}) — verify on official provider site")
        score -= 15
    elif scholarship.trust_score >= 75:
        reasons.append("Higher trust score from discovery filters")

    if scholarship.extraction_confidence and scholarship.extraction_confidence < 50:
        missing.append("Low extraction confidence — confirm details manually")

    if blockers:
        status = "not_eligible"
        score = max(0, min(score, 28))
    elif missing:
        status = "maybe_eligible" if score >= 38 else "missing_info"
        score = max(18, min(score, 68))
    elif score >= 62:
        status = "eligible"
        score = min(95, score + 12)
    else:
        status = "maybe_eligible"

    if scholarship.manual_step_likely and status == "eligible":
        status = "manual_step_needed"

    priority = round(
        score * 0.55 + (100 - scholarship.effort_score) * 0.25 + scholarship.trust_score * 0.2, 1
    )

    return {
        "eligibility_score": round(max(0, min(100, score)), 1),
        "status_recommendation": status,
        "reasons": reasons,
        "blockers": blockers,
        "missing_information": missing,
        "recommended_next_action": _recommended_action(status, scholarship),
        "effort_score": round(scholarship.effort_score, 1),
        "priority_score": priority,
    }


def apply_eligibility_to_scholarship(scholarship: Scholarship, result: dict) -> None:
    scholarship.eligibility_score = result["eligibility_score"]
    scholarship.status = result["status_recommendation"]
    scholarship.eligibility_reasons = "\n".join(result["reasons"]) if result["reasons"] else None
    scholarship.eligibility_blockers = "\n".join(result["blockers"]) if result["blockers"] else None
    scholarship.missing_info = "\n".join(result["missing_information"]) if result["missing_information"] else None
    scholarship.next_action = result.get("recommended_next_action")
    scholarship.effort_score = result.get("effort_score", scholarship.effort_score)
    scholarship.priority_score = result.get("priority_score", scholarship.priority_score)
