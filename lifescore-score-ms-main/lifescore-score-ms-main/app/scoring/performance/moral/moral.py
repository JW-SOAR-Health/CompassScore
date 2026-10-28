from shared_db.enums import DomainEnum
from shared_db.models import UserScore
from sqlalchemy.orm import Session
from .utils import get_life_approach_score


def calculate_moral_score(weekly_report, db: Session):
    """
    Calculate resilience score based on State of Mind,
    Spiritual and Life Approach domains.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: Calculated resilience score
    """
    # Fetch domain scores from the database for the given weekly_id
    domain_scores = {
        domain_score.domain: domain_score.score
        for domain_score in db.query(UserScore)
        .filter(UserScore.weekly_report_id == weekly_report.id)
        .all()
    }

    life_approach_score = get_life_approach_score(weekly_report.id, db)

    state_of_mind_score = domain_scores.get(DomainEnum.STATE_OF_MIND, 0)
    spiritual_score = domain_scores.get(DomainEnum.SPIRITUAL, 0)

    # Apply the resilience formula
    resilience = ((state_of_mind_score + spiritual_score) / 2 * 0.75) + (
        life_approach_score * 0.25
    )

    return round(resilience, 2)
