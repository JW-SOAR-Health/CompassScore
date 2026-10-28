"""
This module contains the functions to calculate the score for cohesion.
"""

from shared_db.enums import CategorySubDomainEnum
from sqlalchemy.orm import Session
from app.scoring.performance.moral.utils import get_life_approach_score
from app.shared_db.models import WeeklyReport
from app.shared_db.crud.helpers.performance_score_helper import get_weight_subdomain
from .utils import get_cohesion_score, get_morale_score
import math


def calculate_cohesion_score(
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
    life_approach_score = get_life_approach_score(weekly_report.id, db)
    cohesion_score = get_cohesion_score(weekly_report, db)
    morale_score = get_morale_score(weekly_report, db)
    spiritual_belief_system_score = get_weight_subdomain(
        weekly_report.user_id, CategorySubDomainEnum.BELIEF_SYSTEM, db
    )
    spiritual_sense_of_purpose_score = get_weight_subdomain(
        weekly_report.user_id, CategorySubDomainEnum.SENSE_OF_PURPOSE, db
    )
    state_of_mind_individual_stress_score = get_weight_subdomain(
        weekly_report.user_id, CategorySubDomainEnum.LIFE_STRESS, db
    )
    final_score = [
        cohesion_score * 0.5,
        morale_score * 0.1,
        (spiritual_belief_system_score / 5) * 10,  # Subdomain scores are out of 5
        (spiritual_sense_of_purpose_score / 5) * 10,
        life_approach_score * 0.1,
        (state_of_mind_individual_stress_score / 5)
        * 10,  # Subdomain scores are out of 5
    ]
    return round(sum(final_score), 2) if math.isfinite(sum(final_score)) else 0.0
