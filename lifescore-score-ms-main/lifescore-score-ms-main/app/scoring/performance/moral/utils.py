import re
from datetime import datetime
from sqlalchemy.orm import Session
from shared_db.models.weekly_report import WeeklyReport
from shared_db.models.life_approach import LifeApproach
from sqlalchemy.sql.sqltypes import UUID


def extract_weekly_report_date(input_string):
    """
    Extracts a date from the end of a string in M-D-Y format.

    Args:
        input_string: The string to extract the date from.

    Returns:
        The extracted date string, or None if no date is found.
    """
    match = re.search(r"(\d{1,2}-\d{1,2}-\d{2,4})$", input_string)
    if match:
        date_string = match.group(1)
        try:
            date_object = datetime.strptime(date_string, "%m-%d-%Y")
            return date_object
        except ValueError:
            try:
                date_object = datetime.strptime(date_string, "%m-%d-%y")
                return date_object
            except ValueError:
                return None
    else:
        return None


def get_life_approach_score(weekly_id: UUID, db: Session):
    """
    Fetch the most relevant Life Approach score based on the weekly report date.

    Args:
        weekly_id (int): The ID of the weekly assessment.
        db (Session): Database session.

    Returns:
        float: The Life Approach score, or 0 if not found.
    """
    # Fetch the weekly report instance
    weekly_report: WeeklyReport = (
        db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    )

    date_to_filter: datetime | None = extract_weekly_report_date(weekly_report.name)

    if date_to_filter:
        life_approach_instance: LifeApproach = (
            db.query(LifeApproach)
            .filter(
                LifeApproach.user_id == weekly_report.user_id,
                LifeApproach.score != 0,
            )
            .order_by(LifeApproach.created_at.desc())
            .first()
        )
    else:
        life_approach_instance = (
            db.query(LifeApproach)
            .filter(
                LifeApproach.user_id == weekly_report.user_id, LifeApproach.score != 0
            )
            .order_by(LifeApproach.created_at.desc())
            .first()
        )

    return life_approach_instance.score if life_approach_instance else 0
