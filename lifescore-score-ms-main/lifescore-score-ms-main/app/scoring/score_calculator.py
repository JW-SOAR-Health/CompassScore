"""
Module for calculating LifeScore and related domain scores.

This module provides the ScoreCalculator class which handles all score calculation
logic, including:
- Domain-specific score calculations using specialized scoring functions
- LifeScore calculation with weighted domain aggregation
- Report name generation and management
- Score persistence and database operations
- Profile updates and task creation

The module uses a collection of domain-specific scoring functions mapped through
the SCORING_FUNCTIONS dictionary, allowing for modular score calculation across
different life domains.

Key Components:
    - ScoreCalculator: Main class handling all scoring operations
    - SCORING_FUNCTIONS: Dictionary mapping domains to their scoring functions
    - DomainEnum: Enumeration of supported life domains

Note:
    The FINANCE domain is currently excluded from score calculations.
"""

import math
from uuid import UUID
from zoneinfo import ZoneInfo
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.scoring import (
    state_of_mind,
    food,
    nutrition,
    sleep,
    spiritual,
    fitness,
    morale,
    cohesion,
    social,
)
from app.scoring.performance import resilience, readiness
from app.scoring.performance import cohesion as cohesion_performance
from app.scoring.performance import social_fitness
from app.shared_db.models import Profile, UserScore, User, WeeklyReport
from app.shared_db.enums import (
    DomainEnum,
    ReportTypeEnum,
    PerformanceDomainEnum,
    CategorySubDomainEnum,
)
from app.shared_db.crud import weekly_reports as crud_weekly_reports
from app.shared_db.crud import answer_group as crud_answer_group
from app.shared_db.crud import user_plan as crud_user_plan
from app.shared_db.crud import (
    user_performance_score as crud_create_user_performance_score,
    user_subdomain_score as crud_subdomain,
)
from app.shared_db.utils.resources_management import get_resources_for_lowest_domains
from app.shared_db.schemas.weekly_report import WeeklyReportCreate, WeeklyReportResponse
from app.shared_db.crud.helpers.assessment_report_helper import (
    _generate_report_name,
    _get_existing_report_scores,
)
from app.shared_db.core.logging_config import get_logger

logger = get_logger(__name__)

PACIFIC_TIMEZONE = ZoneInfo("US/Pacific")

SCORING_FUNCTIONS = {
    DomainEnum.STATE_OF_MIND: state_of_mind.calculate_state_of_mind_score,
    DomainEnum.FOOD: food.calculate_food_score,
    DomainEnum.NUTRITION: nutrition.calculate_nutrition_score,
    DomainEnum.SLEEP: sleep.calculate_sleep_score,
    DomainEnum.SPIRITUAL: spiritual.calculate_spiritual_score,
    DomainEnum.FITNESS: fitness.calculate_fitness_score,
    DomainEnum.MORALE: morale.calculate_morale_score,
    DomainEnum.COHESION: cohesion.calculate_cohesion_score,
    DomainEnum.SOCIAL: social.calculate_social_score,
}

PERFORMANCE_SCORING_FUNCTIONS = {
    PerformanceDomainEnum.RESILIENCE: resilience.calculate_resilience_score,
    PerformanceDomainEnum.UNIT_COHESION: cohesion_performance.calculate_cohesion_score,
    PerformanceDomainEnum.SOCIAL_FITNESS: social_fitness.calculate_social_fitness_score,
    PerformanceDomainEnum.READINESS: readiness.calculate_readiness_score,
}


class ScoreCalculator:
    """
    Handles calculation and persistence of LifeScore and domain scores.

    This class encapsulates all logic related to score calculations, report
    generation, and score persistence. It manages the complete lifecycle of score
    calculation, from individual domain scores to the final weighted LifeScore.

    The calculator handles:
        - Weekly and initial score reports
        - Domain-specific score calculations
        - LifeScore computation with domain weighting
        - Score persistence and database operations
        - Profile updates
        - Task generation based on scores

    Attributes:
        db (Session): SQLAlchemy database session for all database operations
        user (User): Current user for whom scores are being calculated
        user_plan_id (UUID): ID of the user's active plan for context

    Note:
        All database operations are wrapped in transactions to ensure data consistency.
        The class is designed to be instantiated per scoring operation.
    """

    def __init__(self, db: Session, user: User, timezone: ZoneInfo = PACIFIC_TIMEZONE):
        """
        Initialize the ScoreCalculator with necessary context.

        Args:
            db (Session): SQLAlchemy database session for database operations
            user (User): Current user for whom scores will be calculated

        Note:
            The calculator requires all three parameters to function properly.
            The session should be active and the user should exist in the database.
        """
        user_plan = crud_user_plan.get_latest_active_user_plan(db, UUID(str(user.id)))
        if not user_plan:
            raise HTTPException(
                status_code=404, detail="No active user plan found for this user"
            )
        self.db = db
        self.user = user
        self.user_plan_id = UUID(str(user_plan.id))
        self.user_id = UUID(str(user.id))
        self.user_plan = user_plan
        self.timezone = timezone

    def create_new_report(self, report_name: str) -> WeeklyReportResponse:
        """
        Create a new weekly report.

        Initializes a new report record in the database with the given name
        and current context.

        Args:
            report_name (str): Name for the new report

        Returns:
            WeeklyReportResponse: Created report object with metadata

        Note:
            This method does not check for existing reports with the same name.
            That check should be performed before calling this method.
        """

        weekly_report_create = WeeklyReportCreate(
            name=report_name,
            user_id=self.user_id,
            created_at=datetime.now(),
            user_plan_id=self.user_plan_id,
        )
        report = crud_weekly_reports.create_weekly_report(self.db, weekly_report_create)
        return report

    def _calculate_single_domain_score(
        self, domain: DomainEnum
    ) -> tuple[str, float] | None:
        """
        Calculate score for a single domain.

        Args:
            domain (DomainEnum): The domain to calculate score for

        Returns:
            tuple[str, float] | None: A tuple of (domain_name, score) if successful,
                None if calculation fails or no data available

        Note:
            - Returns None if domain is FINANCE or has no scoring function
            - Returns None if no answer groups exist or scoring fails
            - Logs errors but doesn't raise exceptions for individual domain failures
        """
        logger.info("Calculating score for domain %s", domain)
        if domain == DomainEnum.FINANCE or domain not in SCORING_FUNCTIONS:
            logger.info("Domain %s not in scoring functions", domain)
            return None

        try:
            answer_groups = crud_answer_group.get_answer_groups_by_domain_and_user(
                self.db,
                domain=domain,
                user_plan_id=self.user_plan_id,
                group_type=None,
                skip=0,
                limit=100,
            )

            if answer_groups:
                logger.info("Calculating score for domain %s", domain)
                score = SCORING_FUNCTIONS[domain](answer_groups)
                if score is not None:
                    return (domain.value, score)
        except Exception as domain_error:  # pylint: disable=broad-exception-caught
            logger.error(
                "Error calculating score for domain %s: %s",
                domain,
                str(domain_error),
            )

        return None

    def _calculate_domain_scores(self) -> Dict[str, float]:
        """
        Calculate scores for all available domains except FINANCE.

        This function orchestrates the score calculation process for all domains:
        1. Iterates through each domain in DomainEnum
        2. Retrieves relevant answer groups for each domain
        3. Applies domain-specific scoring functions
        4. Aggregates successful calculations into a scores dictionary

        Returns:
            Dict[str, float]: A dictionary mapping domain names to their calculated
            scores.
                Example: {'STATE_OF_MIND': 85.5, 'SLEEP': 90.0, ...}

        Raises:
            HTTPException (404): When no valid scores could be calculated for any domain
            HTTPException (500): When an unexpected error occurs during calculation

        Note:
            - FINANCE domain is explicitly excluded from calculations
            - Each domain uses its specialized scoring function from SCORING_FUNCTIONS
            - Failed domain calculations are logged but don't prevent other calculations
            - At least one valid domain score is required to avoid 404 error
        """
        try:
            scores = {}

            for domain in DomainEnum:
                result = self._calculate_single_domain_score(domain)
                if result:
                    domain_name, score = result
                    scores[domain_name] = score
            logger.info("Domain scores %s", scores)
            if not scores:
                logger.warning("No valid scores could be calculated for any domain")
                raise HTTPException(
                    status_code=404,
                    detail="No scores could be calculated - no valid answer groups",
                )

            return scores

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in _calculate_domain_scores: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error while calculating domain scores: {str(e)}",
            ) from e

    def _calculate_life_score(self, scores: Dict[str, float]) -> float:
        """
        Calculate the overall LifeScore based on individual domain scores.

        Applies a weighted calculation to combine scores from different domains
        into a single LifeScore. Each domain has a specific weight factor:
        - State of Mind: 1.008
        - Sleep: 1.008
        - Spiritual: 0.84
        - Nutrition: 1.014
        - Food: 1.056
        - Fitness: 1.074

        Args:
            scores (Dict[str, float]): Dictionary containing scores for each domain
                Example: {'STATE_OF_MIND': 85.5, 'SLEEP': 90.0, ...}

        Returns:
            float: The calculated LifeScore, rounded to 2 decimal places,
                normalized to a 0-100 scale

        Formula:
            LifeScore = (Σ(domain_score * weight)) / 600 * 100

        Note:
            - Missing domain scores are treated as 0
            - The final score is ceiling-rounded to 2 decimal places
            - The denominator 600 is used for normalization
        """
        try:
            life_score = (
                (
                    scores.get(DomainEnum.STATE_OF_MIND.value, 0) * 1.008
                    + scores.get(DomainEnum.SLEEP.value, 0) * 1.008
                    + scores.get(DomainEnum.SPIRITUAL.value, 0) * 0.84
                    + scores.get(DomainEnum.NUTRITION.value, 0) * 1.014
                    + scores.get(DomainEnum.FOOD.value, 0) * 1.056
                    + scores.get(DomainEnum.FITNESS.value, 0) * 1.074
                )
                / 600
                * 100
            )
            logger.info("Life score %s", life_score)
            return math.ceil(life_score * 100 - 0.5) / 100
        except Exception as e:
            logger.error("Error in _calculate_life_score: %s", str(e))
            raise HTTPException(
                status_code=500, detail=f"Life score calculation failed: {str(e)}"
            ) from e

    def _update_profile_lifescore(self, life_score: float) -> None:
        """
        Update the user's profile with the new LifeScore.

        Args:
            life_score (float): The calculated LifeScore to be saved

        Note:
            - The score is rounded to an integer before saving
            - If no profile exists for the user, no update is performed
        """
        profile = self.db.query(Profile).filter(Profile.user_id == self.user_id).first()
        if profile:
            profile.lifescore = int(round(life_score))
            self.db.add(profile)

    def _save_scores(
        self, weekly_report: WeeklyReportResponse, scores: Dict[str, float]
    ) -> None:
        """
        Save all calculated scores to the database.

        Creates UserScore records for each domain score and the LifeScore,
        associating them with the weekly report and user.

        Args:
            weekly_report (WeeklyReportResponse): The report to associate scores with
            scores (Dict[str, float]): Dictionary of domain names to scores

        Note:
            - The LifeScore is stored with the FINANCE domain enum for historical
            reasons
            - All scores are saved in a single transaction
        """
        # Get the actual WeeklyReport model from the database
        db_weekly_report = (
            self.db.query(WeeklyReport)
            .filter(WeeklyReport.id == weekly_report.id)
            .first()
        )

        if not db_weekly_report:
            raise HTTPException(
                status_code=404,
                detail=f"Weekly report with id {weekly_report.id} not found",
            )

        for domain, score in scores.items():
            user_score = UserScore()
            user_score.weekly_report_id = db_weekly_report.id
            user_score.user_id = self.user.id
            user_score.domain = (
                DomainEnum(domain) if domain != "LifeScore" else DomainEnum.FINANCE
            )
            user_score.name = domain
            user_score.score = score
            self.db.add(user_score)

    async def _create_weekly_report(
        self,
        report_name: str,
        is_initial: bool,
        life_score: float,
        domain_scores: Dict[str, float],
        report_type: ReportTypeEnum,
    ) -> WeeklyReportResponse:
        """
        Create a new weekly report and persist all related data.

        This method handles the complete process of creating a new weekly report,
        including:
        1. Creating the weekly report record
        2. Updating the user's profile with the new LifeScore
        3. Saving all domain scores and the LifeScore
        4. Updating the user plan start date (for initial reports only)
        5. Processing domain scores and creating associated tasks

        Args:
            report_name (str): The unique name for the weekly report
            is_initial (bool): Flag indicating if this is the user's initial report
            life_score (float): The calculated overall LifeScore
            domain_scores (Dict[str, float]): Dictionary of domain scores to save
            report_type (ReportTypeEnum): The type of report being generated
        Raises:
            HTTPException (500): When an error occurs during the save process

        Note:
            - All database operations are performed within a single transaction
            - For initial reports, the user plan start date is set to the current date
            - Tasks are generated based on the domain scores
        """
        try:
            weekly_report = self.create_new_report(report_name)
            self._update_profile_lifescore(life_score)
            self._save_scores(weekly_report, domain_scores)
            self.db.flush()

            if is_initial:
                current_date = datetime.now(self.timezone).date()
                self.user_plan.start_date = current_date  # type: ignore
                logger.info(
                    "User plan start date updated to %s", self.user_plan.start_date
                )
            self.db.flush()
            logger.info("Report type %s", report_type)
            if report_type in {ReportTypeEnum.WEEKLY, ReportTypeEnum.INITIAL}:
                current_week = datetime.now(self.timezone).isocalendar().week
                self.user_plan.current_week = current_week
                logger.info("Updated user plan current_week to %s", current_week)
                self.db.flush()
                logger.info("Processing domain scores and creating tasks")
                crud_weekly_reports.process_domain_scores_and_create_tasks(
                    self.db,
                    UUID(str(weekly_report.id)),
                    self.user_id,
                    self.user_plan_id,
                )
                await get_resources_for_lowest_domains(self.user_id, self.db, False)
            self.db.commit()
            return weekly_report
        except Exception as e:
            logger.error("Failed to save scores and create tasks: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save scores and create tasks: {str(e)}",
            ) from e

    def _handle_existing_report(self, report_name: str) -> Dict[str, float] | None:
        """
        Check for and return existing scores for a given report name.

        Args:
            report_name (str): The name of the report to check for

        Returns:
            Dict[str, float] | None: Existing scores if found, None otherwise
        """
        existing_scores = _get_existing_report_scores(
            self.db, report_name, self.user_id
        )
        logger.info("Existing scores %s", existing_scores)
        return existing_scores if existing_scores else None

    def _calculate_scores(self) -> Dict[str, float]:
        """
        Calculate both domain scores and life score.

        Returns:
            Dict[str, float]: Combined dictionary of domain scores and life score

        Raises:
            HTTPException: If score calculation fails or no valid scores can be
            calculated
        """
        domain_scores = self._calculate_domain_scores()
        if not domain_scores:
            raise HTTPException(
                status_code=404,
                detail="No scores could be calculated - no valid answer groups",
            )

        try:
            life_score = self._calculate_life_score(domain_scores)
            domain_scores["LifeScore"] = life_score
            return domain_scores
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to calculate life score: %s", str(e))
            raise HTTPException(
                status_code=500, detail=f"Life score calculation failed: {str(e)}"
            ) from e

    def _save_performance_score_by_weekly_report(
        self, weekly_report, performance_domain, performance_score
    ) -> None:
        """
        Save performance scores based on the weekly report.

        Calculates and saves performance scores for Resilience, Readiness,
        and Performance Readiness
        based on the provided weekly report.
        """
        crud_create_user_performance_score.create_user_performance_score(
            self.db,
            weekly_report.user_id,
            weekly_report.id,
            performance_domain,
            score=performance_score,
        )

    def _calculate_performance_score(self, weekly_report, domain_scores) -> None:
        for performance_domain, function in PERFORMANCE_SCORING_FUNCTIONS.items():
            logger.info("Calculate performance score for %s", performance_domain)
            performance_score = function(  # type: ignore
                domain_scores,
                weekly_report,
                self.db,
            )
            logger.info("Save performance score %s", performance_score)
            self._save_performance_score_by_weekly_report(
                weekly_report, performance_domain, performance_score
            )

    async def calculate_and_save_all_scores(
        self, is_initial: bool, report_type: ReportTypeEnum
    ) -> Dict[str, float]:
        """
        Calculate and persist all domain scores and the overall LifeScore for a user.

        This method orchestrates the complete scoring process by:
        1. Generating a unique report name based on the scoring period
        2. Checking for existing scores to prevent duplicates
        3. Calculating individual domain scores
        4. Computing the weighted LifeScore
        5. Persisting scores to the database
        6. Creating associated tasks based on the scores
        7. Updating the user's profile with the new LifeScore

        Args:
            is_initial (bool): Flag indicating if this is the user's initial scoring.
                True: Generates an "Initial" report name
                False: Generates a weekly report name with date range
            report_type (ReportTypeEnum): The type of report being generated

        Returns:
            Dict[str, float]: Dictionary containing all calculated scores where:
                - Keys are domain names (str) including 'LifeScore'
                - Values are the calculated scores (float)
                Example: {
                    'STATE_OF_MIND': 85.5,
                    'SLEEP': 90.0,
                    'SPIRITUAL': 75.5,
                    'LifeScore': 82.75
                }

        Raises:
            HTTPException (404): When no scores can be calculated for the user
            HTTPException (500): When an error occurs during score calculation or
            persistence

        Note:
            - All database operations are wrapped in a transaction
            - Existing scores for the same report name are returned without
            recalculation
            - The LifeScore is calculated using weighted domain scores
            - Domain scores are calculated based on user's answer groups
            - The FINANCE domain is excluded from calculations
        """
        try:
            report_name = _generate_report_name(is_initial, report_type)

            # Check for existing report
            domain_scores = self._handle_existing_report(report_name)
            if domain_scores is None:
                logger.info("No existing report found, calculating scores")
                domain_scores = self._calculate_scores()
                logger.info("Domain scores %s", domain_scores)
                # Save scores and create tasks
                await self._create_weekly_report(
                    report_name,
                    is_initial,
                    domain_scores["LifeScore"],
                    domain_scores,
                    report_type,
                )

            weekly_report = crud_weekly_reports.get_weekly_report_by_name_and_user(
                self.db, report_name, self.user_id
            )
            logger.info("Weekly report %s", weekly_report)
            if weekly_report:
                logger.info("Init calculate performance score")
                self._calculate_performance_score(weekly_report, domain_scores)
                logger.info("Init calculate subdomain scores")
                self._calculate_and_save_subdomain_scores(weekly_report)

                self.db.commit()
            return {
                k: v
                for k, v in domain_scores.items()
                if k not in ["morale", "cohesion", "social"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in calculate_and_save_all_scores: %s", str(e)
            )
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during score calculation process: {str(e)}",
            ) from e

    def _get_subdomain_groups_from_categories(self) -> Dict[str, list]:
        """
        Query the categories table to get subdomain groups for specified domains.

        Returns:
            Dict[str, list]: Dictionary mapping domain names to lists of
                CategorySubDomainEnum values
        """
        from sqlalchemy import select
        from app.shared_db.models.question import Category

        # Query categories table for the specified domains
        query = (
            select(Category.domain, Category.sub_domain)
            .where(
                Category.domain.in_(
                    [
                        "STATE_OF_MIND",
                        "SLEEP",
                        "SPIRITUAL",
                        "NUTRITION",
                        "FITNESS",
                        "FOOD",
                    ]
                ),
                Category.sub_domain.isnot(None),
                Category.sub_domain != CategorySubDomainEnum.BMI,
            )
            .order_by(Category.domain, Category.sub_domain)
        )

        result = self.db.execute(query).all()

        # Group subdomains by domain
        subdomain_groups: Dict[str, list] = {}
        for domain, sub_domain in result:
            domain_key = domain.lower()
            if domain_key not in subdomain_groups:
                subdomain_groups[domain_key] = []

            try:
                subdomain_enum = CategorySubDomainEnum(sub_domain)
                subdomain_groups[domain_key].append(subdomain_enum)
            except ValueError:
                logger.warning(
                    "Invalid subdomain %s for domain %s, skipping", sub_domain, domain
                )

        return subdomain_groups

    def _calculate_subdomain_scores(
        self, weekly_report: WeeklyReport
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate subdomain scores for all available subdomains.

        This method calculates scores for all subdomains defined in
        CategorySubDomainEnum using the existing get_weight_subdomain function.
        The scores are organized by their parent domain for better organization.

        Args:
            weekly_report (WeeklyReport): The weekly report to associate scores with

        Returns:
            Dict[str, Dict[str, float]]: Nested dictionary with domain ->
                subdomain -> score
                Example: {
                    'state_of_mind': {
                        'life_stress': 85.5,
                        'family_stress': 70.0
                    },
                    'sleep': {
                        'quantity': 90.0,
                        'quality': 85.0
                    }
                }

        Note:
            - Uses the existing get_weight_subdomain function for consistency
            - Only calculates scores for subdomains that have data
            - Returns 0.0 for subdomains with no data
        """
        from app.shared_db.crud.helpers.performance_score_helper import (
            get_weight_subdomain,
        )

        logger.info("Calculating subdomain scores for user %s", weekly_report.user_id)

        # Query subdomain groups from categories table
        subdomain_groups = self._get_subdomain_groups_from_categories()

        subdomain_scores = {}

        try:
            for domain_name, subdomains in subdomain_groups.items():
                domain_scores = {}
                for subdomain in subdomains:
                    try:
                        score = get_weight_subdomain(
                            weekly_report.user_id,
                            subdomain.value,
                            self.db,
                        )
                        print(f"Subdomain score {subdomain.value}: {score}")
                        domain_scores[subdomain.value] = ((score / 5) * 100).__round__(
                            2
                        )
                        logger.debug(
                            "Calculated subdomain score %s: %s for user %s",
                            subdomain.value,
                            score,
                            weekly_report.user_id,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to calculate score for subdomain %s: %s",
                            subdomain.value,
                            str(e),
                        )
                        domain_scores[subdomain.value] = 0.0
                if domain_scores:
                    subdomain_scores[domain_name] = domain_scores

            logger.info(
                "Successfully calculated subdomain scores for %d domains",
                len(subdomain_scores),
            )
            return subdomain_scores

        except Exception as e:
            logger.error(
                "Error calculating subdomain scores for user %s: %s",
                weekly_report.user_id,
                str(e),
            )
            return {}

    def _save_subdomain_scores(
        self,
        weekly_report: WeeklyReport,
        subdomain_scores: Dict[str, Dict[str, float]],
    ) -> None:
        """
        Save all calculated subdomain scores to the database.

        Creates UserSubdomainScore records for each calculated subdomain score,
        associating them with the weekly report and user.

        Args:
            weekly_report (WeeklyReport): The weekly report to associate scores with
            subdomain_scores (Dict[str, Dict[str, float]]): Nested dictionary of
                domain -> subdomain -> score

        Note:
            - All scores are saved in a single transaction
            - Existing scores for the same report are not deleted (handled by migration)
            - Only saves scores that are greater than 0.0
        """
        logger.info(
            "Saving subdomain scores for user %s, weekly report %s",
            weekly_report.user_id,
            weekly_report.id,
        )

        try:
            saved_count = 0
            skipped_count = 0

            for _, domain_subdomains in subdomain_scores.items():
                for subdomain_name, score in domain_subdomains.items():
                    if score > 0.0:
                        try:
                            subdomain_enum = CategorySubDomainEnum(subdomain_name)

                            existing_score = (
                                crud_subdomain.get_user_sd_score_by_report_and_sd(
                                    db=self.db,
                                    weekly_report_id=UUID(str(weekly_report.id)),
                                    subdomain=subdomain_enum,
                                )
                            )

                            if existing_score:
                                logger.debug(
                                    f"Subdomain score already exists for "
                                    f"{subdomain_name} in weekly report "
                                    f"{weekly_report.id}, skipping",
                                )
                                skipped_count += 1
                                continue

                            crud_subdomain.create_user_subdomain_score(
                                db=self.db,
                                user_id=UUID(str(weekly_report.user_id)),
                                weekly_report_id=UUID(str(weekly_report.id)),
                                subdomain=subdomain_enum,
                                name=subdomain_name,
                                score=score,
                            )
                            saved_count += 1

                        except ValueError:
                            logger.warning(
                                "Invalid subdomain name: %s, skipping",
                                subdomain_name,
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to save subdomain score %s: %s",
                                subdomain_name,
                                str(e),
                            )

            logger.info(
                "Successfully saved %d subdomain scores for user %s "
                "(skipped %d existing)",
                saved_count,
                weekly_report.user_id,
                skipped_count,
            )

        except Exception as e:
            logger.error(
                "Error saving subdomain scores for user %s: %s",
                weekly_report.user_id,
                str(e),
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to save subdomain scores: {str(e)}"
            ) from e

    def _calculate_and_save_subdomain_scores(self, weekly_report: WeeklyReport) -> None:
        """
        Calculate and save subdomain scores for a weekly report.

        This method orchestrates the complete subdomain scoring process:
        1. Calculates scores for all available subdomains
        2. Saves the calculated scores to the database

        Args:
            weekly_report (WeeklyReport): The weekly report to process

        Note:
            - This method is called after domain and performance scores are calculated
            - All operations are performed within the existing database transaction
        """
        try:
            logger.info(
                "Starting subdomain score calculation for user %s",
                weekly_report.user_id,
            )

            # Calculate subdomain scores
            subdomain_scores = self._calculate_subdomain_scores(weekly_report)

            if subdomain_scores:
                # Save subdomain scores
                self._save_subdomain_scores(weekly_report, subdomain_scores)
                logger.info(
                    "Completed subdomain score calculation and saving for user %s",
                    weekly_report.user_id,
                )
            else:
                logger.warning(
                    "No subdomain scores calculated for user %s",
                    weekly_report.user_id,
                )

        except Exception as e:
            logger.error(
                "Error in subdomain score calculation and saving for user %s: %s",
                weekly_report.user_id,
                str(e),
            )
            # Don't raise the exception to avoid breaking the main scoring flow
            # Just log the error and continue
