"""
API endpoints for scoring.

This module provides FastAPI routes and utility functions for managing and calculating
user scores across different life domains (State of Mind, Food, Nutrition, Sleep,
Spiritual, and Fitness). It handles weekly report generation, score calculations,
and score retrieval operations.

Key Features:
- Domain-specific score calculation
- Weekly report generation and management
- Overall LifeScore calculation based on weighted domain scores
- Secure endpoints with user authentication
- Historical weekly report retrieval

Dependencies:
- FastAPI for API routing
- SQLAlchemy for database operations
- Custom scoring modules for each domain
- Shared database models and schemas

The module uses a scoring system where each domain contributes differently to the final
LifeScore, with weights ranging from 0.84 to 1.074 depending on the domain's importance.
"""

from typing import Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared_db.database import get_db
from app.shared_db.crud import (
    user_plan as crud_user_plan,
    answer_group as crud_answer_group,
)
from app.shared_db.enums import DomainEnum, ReportTypeEnum
from app.shared_db.models.users import User
from app.shared_db.schemas.weekly_report import WeeklyReportRequest
from app.shared_db.core.logging_config import get_logger
from app.core.security import get_current_user
from app.scoring.score_calculator import ScoreCalculator, SCORING_FUNCTIONS
from app.shared_db.middlewares.verify_token_route import VerifyTokenRoute

logger = get_logger(__name__)

protected_router = APIRouter(
    responses={404: {"description": "not found"}},
    route_class=VerifyTokenRoute,
)

router = APIRouter(
    responses={404: {"description": "not found"}},
)


@router.get(
    "/score/{domain}/user/{user_id}",
    response_model=Dict[str, float],
)
def get_score_by_domain_and_user(
    domain: DomainEnum,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Retrieve and calculate the score for a specific domain and user.

    Args:
        domain (DomainEnum): The domain to calculate the score for.
        user_id (UUID): The ID of the user.
        skip (int, optional): Number of records to skip. Defaults to 0.
        limit (int, optional): Maximum number of records to return. Defaults to 100.
        db (Session): The database session.

    Returns:
        Dict[str, float]: A dictionary containing the calculated score.

    Raises:
        HTTPException: If the domain is not supported, if no active user plan is found,
                       or if no score could be calculated.
    """
    if domain not in SCORING_FUNCTIONS:
        raise HTTPException(status_code=400, detail="Unsupported domain")

    # Get the active user plan for the user
    user_plan = crud_user_plan.get_latest_active_user_plan(db, user_id)
    if not user_plan:
        raise HTTPException(
            status_code=404, detail="No active user plan found for this user"
        )
    print(user_plan.id)
    answer_groups = crud_answer_group.get_answer_groups_by_domain_and_user(
        db,
        domain=domain,
        user_plan_id=UUID(str(user_plan.id)),
        group_type=None,
        skip=skip,
        limit=limit,
    )

    if not answer_groups:
        raise HTTPException(
            status_code=404,
            detail="No answer groups found for this domain and user",
        )

    score_function = SCORING_FUNCTIONS[domain]
    score = score_function(answer_groups)

    if score is None:
        raise HTTPException(
            status_code=404,
            detail="No score could be calculated for this domain and user",
        )

    return {"score": score}


@protected_router.post("/weekly-report-token", response_model=Dict[str, float])
async def create_weekly_report_secured(
    request: WeeklyReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, float]:
    """
    Create a weekly report for all domains using the ScoreCalculator.

    This endpoint handles the creation of weekly reports, calculating scores
    for all domains and the overall LifeScore. It uses the ScoreCalculator
    class to manage all score calculations and persistence.

    Args:
        request (WeeklyReportRequest): Contains is_initial flag for report type
        db (Session): Database session from dependency
        current_user (User): Authenticated user from dependency

    Returns:
        Dict[str, float]: Dictionary containing all calculated scores,
            including domain scores and LifeScore

    Raises:
        HTTPException (404): If no active user plan is found
        HTTPException (500): If score calculation fails
    """

    # Initialize calculator and process scores
    calculator = ScoreCalculator(db=db, user=current_user)

    return await calculator.calculate_and_save_all_scores(
        is_initial=request.is_initial, report_type=request.report_type
    )


@router.post("/weekly-report/{user_id}", response_model=Dict[str, float])
async def create_weekly_report(
    user_id: UUID,
    request: WeeklyReportRequest,
    db: Session = Depends(get_db),
) -> Dict[str, float]:
    """
    Create a weekly report for all domains using the ScoreCalculator.

    This endpoint provides the same functionality as create_weekly_report_secured
    but accepts a user_id parameter instead of using token authentication.

    Args:
        user_id (UUID): ID of the user to calculate scores for
        request (WeeklyReportRequest): Contains is_initial flag for report type
        db (Session): Database session from dependency

    Returns:
        Dict[str, float]: Dictionary containing all calculated scores,
            including domain scores and LifeScore

    Raises:
        HTTPException (404): If user not found or no active user plan exists
        HTTPException (500): If score calculation fails
    """
    # Validate user and plan
    logger.info("Create weekly report for user %s", user_id)
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_plan = crud_user_plan.get_latest_active_user_plan(db, user_id)
    if not user_plan:
        raise HTTPException(
            status_code=404, detail="No active user plan found for this user"
        )

    # Initialize calculator and process scores
    calculator = ScoreCalculator(db=db, user=current_user)

    return await calculator.calculate_and_save_all_scores(
        is_initial=request.is_initial, report_type=request.report_type
    )


@router.post("/generate-all-weekly-reports", response_model=Dict[str, int])
async def generate_all_weekly_reports(
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """
    Generate weekly reports for all active users who have completed their initial
    assessment.

    This endpoint performs a batch operation to generate weekly reports for all eligible
    users in the system. Eligible users are those who:
    - Have an active account (is_active = True)
    - Have not been deleted (is_deleted = False)
    - Have completed their initial assessment (initial_assessment_completed = True)

    The function processes each user individually and maintains counts of successful
    and failed report generations. If a report generation fails for one user, the
    process continues with the remaining users to ensure maximum completion.

    Args:
        request (WeeklyReportRequest): Contains configuration for report generation
            - is_initial (bool): Flag indicating if this is an initial report
            - report_type (ReportTypeEnum): Type of report to generate (e.g., WEEKLY)
        db (Session): Database session from dependency injection

    Returns:
        Dict[str, int]: A dictionary containing processing statistics:
            - total_processed: Total number of eligible users found
            - successful: Number of reports successfully generated
            - failed: Number of report generations that failed

    Raises:
        HTTPException (500): If there's a critical error in the batch process

    Example Response:
        {
            "total_processed": 100,
            "successful": 98,
            "failed": 2
        }

    Technical Details:
        - Uses SQLAlchemy query filtering for user selection
        - Implements individual error handling per user
        - Utilizes the ScoreCalculator class for consistent score calculation
        - Maintains transaction isolation per user

    Performance Considerations:
        - Processes users sequentially to prevent database overload
        - Logs failures individually for debugging purposes
        - Continues processing despite individual failures
    """
    logger.info("Starting batch weekly report generation")

    # Query for eligible users
    try:
        eligible_users = (
            db.query(User)
            .filter(
                User.is_active,
                ~User.is_deleted,
                User.initial_assessment_completed,
            )
            .all()
        )

        logger.info(
            "Found %d eligible users for report generation", len(eligible_users)
        )
    except Exception as e:
        error_msg = "Failed to query eligible users"
        logger.error("%s: %s", error_msg, str(e))
        raise HTTPException(status_code=500, detail=error_msg) from e

    success_count = 0
    failure_count = 0

    # Process each user
    for user in eligible_users:
        try:
            logger.debug("Processing report for user %s", user.id)
            calculator = ScoreCalculator(db=db, user=user)
            await calculator.calculate_and_save_all_scores(
                is_initial=False, report_type=ReportTypeEnum.WEEKLY
            )
            success_count += 1
            logger.info("Successfully generated report for user %s", user.id)
        except Exception as e:
            failure_count += 1
            logger.error(
                "Failed to generate report for user %s: %s",
                user.id,
                str(e),
                exc_info=True,
            )

    result = {
        "total_processed": len(eligible_users),
        "successful": success_count,
        "failed": failure_count,
    }

    logger.info("Completed batch report generation. Results: %s", result)

    return result
