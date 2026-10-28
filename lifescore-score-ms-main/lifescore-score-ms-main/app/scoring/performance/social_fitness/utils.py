from sqlalchemy.orm import Session
from app.shared_db.models.weekly_report import WeeklyReport
from app.shared_db.models import UserScore
from app.shared_db.models.life_approach import (
    LifeApproach,
    LifeApproachQuestion,
    LifeApproachAnswer,
)
from app.shared_db.enums import DomainEnum


def get_social_score(weekly_report: WeeklyReport, db: Session) -> float:
    """
    Fetch the most relevant Life Approach score based on the weekly report date.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: The Life Approach score, or 0 if not found.
    """
    social = (
        db.query(UserScore)
        .filter(
            UserScore.weekly_report_id == weekly_report.id,
            UserScore.domain == DomainEnum.SOCIAL,
        )
        .first()
    )

    if social:
        return social.score

    return 0.0


def get_life_approach_extrovert_score(weekly_report, db: Session) -> float:
    """
    Fetch the most relevant Life Approach score based on the weekly report date.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: The Life Approach score, or 0 if not found.
    """
    question = (
        db.query(LifeApproachQuestion)
        .filter(LifeApproachQuestion.text.icontains("Do you consider yourself"))
        .first()
    )

    if not question:
        return 0.0

    answer: LifeApproachAnswer | None = (
        db.query(LifeApproachAnswer)
        .join(LifeApproach, LifeApproachAnswer.life_approach_id == LifeApproach.id)
        .filter(
            LifeApproachAnswer.life_approach_question_id == question.id,
            LifeApproach.user_id == weekly_report.user_id,
        )
        .order_by(LifeApproachAnswer.id.desc())
        .first()
    )

    return float(answer.life_approach.score) / 11 if answer else 0.0
