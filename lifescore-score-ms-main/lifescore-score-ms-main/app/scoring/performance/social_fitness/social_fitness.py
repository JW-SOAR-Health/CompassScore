"""
This module contains the functions to calculate the score for cohesion.
"""

from shared_db.enums import DomainEnum, CategorySubDomainEnum
from sqlalchemy.orm import Session
from app.shared_db.models import WeeklyReport
from app.shared_db.crud.helpers.performance_score_helper import get_weight_subdomain
from .utils import get_social_score, get_life_approach_extrovert_score
import math


def calculate_social_fitness_score(
    domain_scores, weekly_report: WeeklyReport, db: Session
) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects for the cohesion domain.

    Args:
        answer_groups (List[AnswerGroup]): A list of AnswerGroup objects.

    Returns:
        float: The calculated cohesion score.
    """
    if not domain_scores:
        return 0.0

    # Calculate the general score for the cohesion domain
    social_score = get_social_score(weekly_report, db)
    lifeapproach_extrovert_score = get_life_approach_extrovert_score(weekly_report, db)
    spiritual_domain_score = domain_scores.get(DomainEnum.SPIRITUAL, 0)
    state_of_mind_life_stress_score = get_weight_subdomain(
        weekly_report.user_id, CategorySubDomainEnum.LIFE_STRESS, db
    )

    final_score = [
        social_score * 0.65,
        lifeapproach_extrovert_score * 0.1,
        spiritual_domain_score * 0.5,
        state_of_mind_life_stress_score / 5 * 10,  # Subdomain scores are out of 5
    ]
    return round(sum(final_score), 2) if math.isfinite(sum(final_score)) else 0.0
