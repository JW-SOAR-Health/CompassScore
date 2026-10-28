"""
This file contains the fixtures for the tests.
"""

from typing import Dict, Union
import uuid
import json
import asyncio
import pytest
from httpx import AsyncClient

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import event, String, TypeDecorator
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.types import TEXT

from ..shared_db.database import Base
from ..main import app

# noqa: F403, F401
from ..shared_db.models import *  # noqa: F401, F403, W0401, W0614
from ..shared_db.models import (
    Area,
    Category,
    AnswerOption,
    WeeklyReport,
    AssessmentSchedule,
    Question,
    UserPlan,
    AnswerGroup,
    User,
)
from ..shared_db.enums.questions_enum import (
    AnswerOptionTypeEnum,
    DomainEnum,
    CategorySubDomainEnum,
    QuestionTypeEnum,
    AnswerGroupTypeEnum,
)


class SQLiteUUID(TypeDecorator):
    """
    Custom type decorator for handling UUIDs in SQLite.

    This class converts UUID objects to strings for storage in the database
    and converts them back to UUID objects when retrieved.
    """

    impl = String

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return str(value)
        else:
            return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def sqlite_uuid_generator():
    """
    Generate a random UUID string.

    This function is used to create a new UUID string, which can be used
    as a default value for UUID fields in the database.
    """
    return str(uuid.uuid4())


# Set up an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)


# Add the custom UUID function to SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set the SQLite foreign keys pragma."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")

    # Add UUID support
    dbapi_connection.create_function("gen_random_uuid", 0, sqlite_uuid_generator)

    cursor.close()


# Override UUID type handling
sqlite_dialect.ischema_names["uuid"] = SQLiteUUID


class SQLiteArray(TypeDecorator):
    """
    Custom type decorator for handling arrays in SQLite.

    This class converts Python lists to JSON strings for storage in the database
    and converts them back to Python lists when retrieved.
    """

    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


@event.listens_for(Base.metadata, "before_create")
def receive_before_create(target, connection, **kw):
    """Override UUID and ARRAY type handling for SQLite."""
    for table in target.tables.values():
        for column in table.columns:
            if column.type.__class__.__name__ == "UUID":
                column.type = SQLiteUUID()
                if column.server_default is not None and "gen_random_uuid()" in str(
                    column.server_default
                ):
                    column.server_default = None
                    column.default = lambda: connection.scalar(
                        "SELECT gen_random_uuid()"
                    )
            elif column.type.__class__.__name__ == "ARRAY":
                column.type = SQLiteArray()


# Create a sessionmaker for async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a new asyncio event loop for the test session.

    This fixture is used to provide an event loop for asynchronous tests.
    It creates a new event loop at the start of the session and closes it at the end.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_app():
    """
    Provide the test application instance.

    This fixture yields the application instance used for testing.
    Any setup or teardown actions related to the app can be added here.
    """
    # Any setup actions can be placed here
    yield app
    # Any teardown actions can be placed here


@pytest.fixture(scope="session")
async def async_client(test_app):
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def client(async_client):
    """
    Provide an asynchronous HTTP client for testing.

    This fixture yields an instance of AsyncClient, which can be used to make
    HTTP requests to the test application.
    """
    yield async_client


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def clean_db(db_session):
    """Clean up the database after each test."""
    yield db_session
    await db_session.rollback()


@pytest.fixture(scope="function")
async def sample_data(
    db_session: AsyncSession,
) -> Dict[str, Union[Area, Category, AnswerOption]]:
    """
    Create and return sample data for testing.

    This fixture creates instances of Area, Category, and AnswerOption,
    adds them to the database session, and returns them in a dictionary.

    Args:
        db_session (AsyncSession): The database session to use for adding
        the sample data.

    Returns:
        Dict[str, Union[Area, Category, AnswerOption]]: A dictionary containing the
        created instances,
        with keys 'area', 'category', and 'answer_option'.
    """
    area = Area()
    area.name = "Test Area"
    area.text = "Test Area Description"

    category = Category()
    category.name = "Test Category"
    category.domain = DomainEnum.HEALTH
    category.sub_domain = CategorySubDomainEnum.BELIEF_SYSTEM

    answer_option = AnswerOption()
    answer_option.name = "Test Answer Option"
    answer_option.type = AnswerOptionTypeEnum.SINGLE_CHOICE

    db_session.add_all([area, category, answer_option])
    await db_session.commit()

    return {"area": area, "category": category, "answer_option": answer_option}


@pytest.fixture(scope="function")
async def test_user(db_session):
    """Create a test user."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture(scope="function")
async def test_assessment_schedule(db_session):
    """Create a test assessment schedule."""
    assessment_schedule = AssessmentSchedule(
        name="Test Schedule", schedule="Daily", is_active=True
    )
    db_session.add(assessment_schedule)
    await db_session.commit()
    return assessment_schedule


@pytest.fixture(scope="function")
async def test_user_plan(db_session, test_user, test_assessment_schedule):
    """Create a test user plan."""
    user_plan = UserPlan(
        assessment_schedule_id=test_assessment_schedule.id,
        quantity_days=30,
        user_id=test_user.id,
    )
    db_session.add(user_plan)
    await db_session.commit()
    return user_plan


@pytest.fixture(scope="function")
async def test_weekly_report(db_session, test_user, test_user_plan):
    """Create a test weekly report."""
    weekly_report = WeeklyReport(
        user_id=test_user.id,
        user_plan_id=test_user_plan.id,
        name="Weekly Report",
    )
    db_session.add(weekly_report)
    await db_session.commit()
    return weekly_report


@pytest.fixture(scope="function")
async def test_questions(db_session):
    """Create test questions."""
    # First, we need to create an Area, Category, and AnswerOption
    area = Area(name="Test Area", text="Test Area Description")
    category = Category(name="Test Category", domain=DomainEnum.HEALTH)
    answer_option = AnswerOption(
        name="Test Answer Option", type=AnswerOptionTypeEnum.SINGLE_CHOICE
    )
    db_session.add_all([area, category, answer_option])
    await db_session.flush()  # This will assign ids to the objects

    questions = [
        Question(
            area_id=area.id,
            answer_option_id=answer_option.id,
            category_id=category.id,
            text="How many hours did you sleep?",
            name="question1",
            type=QuestionTypeEnum.BOOLEAN,  # Add this line
            is_female=False,
            is_active=True,
        ),
        Question(
            area_id=area.id,
            answer_option_id=answer_option.id,
            category_id=category.id,
            text="Did you exercise today?",
            name="question2",
            type=QuestionTypeEnum.BOOLEAN,  # Add this line
            is_female=False,
            is_active=True,
        ),
        Question(
            area_id=area.id,
            answer_option_id=answer_option.id,
            category_id=category.id,
            text="How productive were you today?",
            name="question3",
            type=QuestionTypeEnum.SCALE,  # Add this line
            is_female=False,
            is_active=True,
        ),
    ]
    db_session.add_all(questions)
    await db_session.commit()
    return questions


@pytest.fixture(scope="function")
async def test_answer_groups(db_session, test_user_plan, test_questions):
    """Create test answer groups."""
    answer_groups = []
    for i in range(3):
        answer_group = AnswerGroup(
            user_plan_id=test_user_plan.id,
            is_active=True,
            weight=50,
            quantity_days=7,
            domain=DomainEnum.HEALTH,
            group_type=AnswerGroupTypeEnum.DAILY,
            question_id=test_questions[i].id,
        )
        db_session.add(answer_group)
        answer_groups.append(answer_group)

    await db_session.commit()
    return answer_groups
