"""Eligibility engine — scores scholarships against profile without guessing."""
from datetime import date
from app.models.profile import Profile
from app.models.scholarship import Scholarship


def _contains(text: str | None, *terms: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(t.lower() in lower for t in terms)


def evaluate_eligibility(profile: Profile | None, scholarship: Scholarship) -> dict:
    reasons: list[str] = []
    blockers: list[str] = []
    missing: list[str] = []
    score = 50.0

    if scholarship.deadline and scholarship.deadline < date.today():
        blockers.append("Deadline has passed")
        return {
            "eligibility_score": 0.0,
            "status_recommendation": "not_eligible",
            "reasons": reasons,
            "blockers": blockers,
            "missing_information": missing,
        }

    if not profile:
        missing.append("Profile not configured — complete Profile Vault")
        return {
            "eligibility_score": 25.0,
            "status_recommendation": "missing_info",
            "reasons": reasons,
            "blockers": blockers,
            "missing_information": missing,
        }

    # Major match
    if scholarship.major_requirement:
        if profile.major:
            if _contains(scholarship.major_requirement, "mechanical", "engineering"):
                if _contains(profile.major, "mechanical", "engineering"):
                    reasons.append("Major aligns with Mechanical Engineering")
                    score += 15
                else:
                    blockers.append(f"Major requirement may not match: {scholarship.major_requirement}")
                    score -= 20
            elif _contains(profile.major, scholarship.major_requirement.split()[0]):
                reasons.append("Major appears compatible")
                score += 10
            else:
                missing.append(f"Verify major requirement: {scholarship.major_requirement}")
                score -= 5
        else:
            missing.append("Your major is not set in profile")

    # International student
    intl = scholarship.international_allowed.lower()
    if intl == "no" and profile.international_student:
        blockers.append("Scholarship appears limited to citizens/permanent residents")
        score -= 40
    elif intl == "yes" and profile.international_student:
        reasons.append("International students explicitly allowed")
        score += 15
    elif intl == "unknown" and profile.international_student:
        missing.append("International student eligibility unclear — verify on portal")
        score -= 5

    if scholarship.citizenship_requirement:
        if _contains(scholarship.citizenship_requirement, "us citizen", "u.s. citizen") and profile.international_student:
            blockers.append(f"Citizenship restriction: {scholarship.citizenship_requirement}")
            score -= 35
        elif not profile.visa_status and profile.international_student:
            missing.append("Visa status not in profile — needed for citizenship checks")

    if scholarship.education_level_requirement and not profile.education:
        missing.append("Education level in profile needed to match requirement")

    if scholarship.eligibility_notes and profile.gpa is None and "gpa" in scholarship.eligibility_notes.lower():
        missing.append("GPA required but not in profile")

    if profile.gpa and scholarship.eligibility_notes and "gpa" in scholarship.eligibility_notes.lower():
        reasons.append(f"GPA on file: {profile.gpa}")

    if scholarship.essay_required:
        reasons.append("Essay required — plan time in Essay Studio")

    if blockers:
        status = "not_eligible"
        score = max(0, min(score, 30))
    elif missing:
        status = "maybe_eligible" if score >= 40 else "missing_info"
        score = max(20, min(score, 70))
    elif score >= 65:
        status = "eligible"
        score = min(100, score + 10)
    else:
        status = "maybe_eligible"

    return {
        "eligibility_score": round(max(0, min(100, score)), 1),
        "status_recommendation": status,
        "reasons": reasons,
        "blockers": blockers,
        "missing_information": missing,
    }


def apply_eligibility_to_scholarship(scholarship: Scholarship, result: dict) -> None:
    scholarship.eligibility_score = result["eligibility_score"]
    scholarship.status = result["status_recommendation"]
    scholarship.eligibility_reasons = "\n".join(result["reasons"]) if result["reasons"] else None
    scholarship.eligibility_blockers = "\n".join(result["blockers"]) if result["blockers"] else None
    scholarship.missing_info = "\n".join(result["missing_information"]) if result["missing_information"] else None
    scholarship.priority_score = round(
        scholarship.eligibility_score * 0.6 + (100 - scholarship.effort_score) * 0.2 + scholarship.trust_score * 0.2,
        1,
    )
