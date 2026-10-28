from sqlalchemy.orm import Session
from app.scoring.performance.moral.utils import get_life_approach_score
from app.shared_db.models import WeeklyReport, UserPerformanceScore
from shared_db.enums import DomainEnum
from shared_db.core.logging_config import get_logger
from shared_db.enums import PerformanceDomainEnum

logger = get_logger(__name__)


def calculate_readiness_score(domain_scores, weekly_report: WeeklyReport, db: Session):
    """
    Calculate performance readiness score based on the resilience, lifeapproach, morale,
    social fitness, unit cohesion domains.

    Args:
        domain_scores (dict): A dictionary containing the scores for the resilience,
        lifeapproach, morale, social fitness, and unit cohesion domains.
        weekly_report (WeeklyReport): The weekly report object.
        db (Session): The database session.

    """
    try:
        logger.info("Calculate readiness score")
        resilience_score: float = 0.0
        social_fitness_score: float = 0.0
        cohesion_score: float = 0.0
        user_performance_score = (
            db.query(
                UserPerformanceScore.performance_domain, UserPerformanceScore.score
            )
            .filter(UserPerformanceScore.weekly_report_id == weekly_report.id)
            .all()
        )

        if user_performance_score:
            for domain, score in user_performance_score:
                if domain == PerformanceDomainEnum.RESILIENCE:
                    resilience_score = score * 0.1
                elif domain == PerformanceDomainEnum.SOCIAL_FITNESS:
                    social_fitness_score = score * 0.05
                elif domain == PerformanceDomainEnum.UNIT_COHESION:
                    cohesion_score = score * 0.05

        lifescore_score = domain_scores.get("LifeScore", 0) * 0.55
        life_approach_score = get_life_approach_score(weekly_report.id, db) * 0.2
        morale_score = domain_scores.get(DomainEnum.MORALE, 0) * 0.05

        logger.debug(
            "Resilience score: %s for user %s",
            resilience_score,
            weekly_report.user_id,
        )
        logger.debug(
            "Social fitness score: %s for user %s",
            social_fitness_score,
            weekly_report.user_id,
        )
        logger.debug(
            "Cohesion score: %s for user %s",
            cohesion_score,
            weekly_report.user_id,
        )
        logger.debug(
            "Life approach score: %s for user %s",
            life_approach_score,
            weekly_report.user_id,
        )
        logger.debug(
            "Morale score: %s for user %s", morale_score, weekly_report.user_id
        )

        readiness_score = (
            lifescore_score
            + life_approach_score
            + morale_score
            + social_fitness_score
            + cohesion_score
            + resilience_score
        )

        logger.debug(
            "Readiness score: %s for user %s",
            readiness_score,
            weekly_report.user_id,
        )

        return round(readiness_score, 2)
    except Exception as e:
        logger.error("Error calculating readiness score: %s", str(e))
        raise
