from sqlalchemy.orm import Session
from app.shared_db.models.weekly_report import WeeklyReport
from app.shared_db.models import UserScore
from app.shared_db.enums import DomainEnum


def get_cohesion_score(weekly_report: WeeklyReport, db: Session) -> float:
    """
    Fetch the most relevant Life Approach score based on the weekly report date.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: The Life Approach score, or 0 if not found.
    """
    cohesion = db.query(UserScore).filter(
        UserScore.weekly_report_id == weekly_report.id,
        UserScore.domain == DomainEnum.COHESION,
    )
    if cohesion and cohesion.count() > 0:
        cohesion_score = cohesion.first()
        if cohesion_score:
            return cohesion_score.score

    return 0.0


def get_morale_score(weekly_report: WeeklyReport, db: Session) -> float:
    """
    Fetch the most relevant Life Approach score based on the weekly report date.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: The Life Approach score, or 0 if not found.
    """
    morale = db.query(UserScore).filter(
        UserScore.weekly_report_id == weekly_report.id,
        UserScore.domain == DomainEnum.MORALE,
    )

    if morale and morale.count() > 0:
        morale_score = morale.first()
        if morale_score:
            return morale_score.score

    return 0.0
