"""
This module contains test cases for the questions API endpoints.

It includes tests for batch operations on areas, answer options, categories, and
questions, as well as tests for domain validation and retrieval. The tests use an
in-memory SQLite database to ensure isolation and fast execution.

The test cases cover:
1. Batch upsert of areas
2. Batch upsert of answer options
3. Batch upsert of categories
4. Batch create or update of questions
5. Domain validation
6. Retrieval of all domains

Each test function focuses on a specific endpoint and verifies its functionality
by sending requests and asserting the responses.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import db_session, async_client, sample_data  # noqa: F401, W0611
from ..main import app
from ..shared_db.enums.questions_enum import (
    AnswerOptionTypeEnum,
    QuestionTypeEnum,
    DomainEnum,
    CategorySubDomainEnum,
)
from ..shared_db import models


@pytest.mark.asyncio
async def test_uuid_generation(db_session):
    area = models.Area(name="Test Area", text="Test Area Description")
    db_session.add(area)
    await db_session.commit()

    assert area.id is not None
    print(f"Generated UUID: {area.id}")


@pytest.mark.asyncio
async def test_upsert_areas_batch(async_client: AsyncClient, db_session: AsyncSession):
    """
    Test the batch upsert operation for areas.

    This test sends a POST request to create multiple areas and verifies
    that the response contains the correct number of areas with the expected names.
    """
    areas_data = [
        {"name": "Area 1", "text": "Description 1"},
        {"name": "Area 2", "text": "Description 2"},
    ]

    # Debug: Print areas_data to ensure IDs are not set
    print("Areas data before POST:", areas_data)

    response = await async_client.post("/questions/areas/batch/", json=areas_data)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Area 1"
    assert response.json()[1]["name"] == "Area 2"


@pytest.mark.asyncio
async def test_upsert_answer_options_batch(async_client: AsyncClient):
    """
    Test the batch upsert operation for answer options.
    """
    answer_options_data = [
        {
            "name": "Option 1",
            "type": AnswerOptionTypeEnum.SINGLE_CHOICE.value,
            "option1": "Choice 1",
            "option2": "Choice 2",
            "is_active": True,
        },
        {
            "name": "Option 2",
            "type": AnswerOptionTypeEnum.MULTIPLE_CHOICE.value,
            "option_multi": "Choice A, Choice B, Choice C",
            "is_active": True,
        },
    ]
    response = await async_client.post(
        "/questions/answer-options/batch/", json=answer_options_data
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Option 1"
    assert response.json()[1]["name"] == "Option 2"


@pytest.mark.asyncio
async def test_upsert_categories_batch(async_client: AsyncClient):
    """
    Test the batch upsert operation for categories.
    """
    categories_data = [
        {
            "name": "Category 1",
            "text": "Description 1",
            "domain": DomainEnum.FITNESS.value,
            "sub_domain": CategorySubDomainEnum.LIFE_STRESS.value,
        },
        {
            "name": "Category 2",
            "text": "Description 2",
            "domain": DomainEnum.FOOD.value,
            "sub_domain": CategorySubDomainEnum.QUALITY.value,
        },
    ]
    response = await async_client.post(
        "/questions/categories/batch/", json=categories_data
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Category 1"
    assert response.json()[1]["name"] == "Category 2"


@pytest.mark.asyncio
async def test_create_or_update_questions_batch(
    async_client: AsyncClient, db_session: AsyncSession, sample_data
):
    """
    Test the batch create or update operation for questions.
    """
    # First, create necessary related objects
    area = sample_data["area"]
    category = sample_data["category"]
    answer_option = sample_data["answer_option"]
    db_session.add_all([area, category, answer_option])
    await db_session.commit()

    questions_data = [
        {
            "name": "Question 1",
            "text": "What is question 1?",
            "type": QuestionTypeEnum.MULTIPLE_CHOICE.value,
            "area_name": "Test Area",
            "category_name": "Test Category",
            "answer_option_name": "Test Option",
            "is_female": False,
            "is_active": True,
        },
        {
            "name": "Question 2",
            "text": "What is question 2?",
            "type": QuestionTypeEnum.OPEN_ENDED.value,
            "area_name": "Test Area",
            "category_name": "Test Category",
            "answer_option_name": "Test Option",
            "is_female": True,
            "is_active": True,
        },
    ]
    response = await async_client.post(
        "/questions/questions/batch/", json=questions_data
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Question 1"
    assert response.json()[1]["name"] == "Question 2"


@pytest.mark.asyncio
async def test_validate_domain(async_client: AsyncClient):
    """
    Test the domain validation endpoint.

    This test sends GET requests to validate both a valid and an invalid domain.
    It verifies that the endpoint correctly identifies valid and invalid domains.
    """
    valid_domain = DomainEnum.FITNESS.value
    invalid_domain = "INVALID_DOMAIN"

    response = await async_client.get(f"/questions/domains/validate/{valid_domain}")
    assert response.status_code == 200
    assert response.json() == {"is_valid": True}

    response = await async_client.get(f"/questions/domains/validate/{invalid_domain}")
    assert response.status_code == 200
    assert response.json() == {"is_valid": False}


def test_read_domains():
    """
    Test the endpoint for retrieving all domains.

    This test sends a GET request to retrieve all domains and verifies that
    the response is a list containing expected domain values.
    """
    response = client.get("/questions/domains/")
    assert response.status_code == 200
    domains = response.json()
    assert isinstance(domains, list)

    for domain in DomainEnum:
        assert domain.value in domains
