"""
This module contains the functions to calculate the score for food.
"""

from typing import List
from shared_db.models.answer_group import AnswerGroup
from .general_score import calculate_general_score


def calculate_food_score(answer_groups: List[AnswerGroup]) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects for the food domain.

    Args:
        answer_groups (List[AnswerGroup]): A list of AnswerGroup objects.

    Returns:
        float: The calculated food score.
    """
    return calculate_general_score(answer_groups, scale_factor=55 / 30, offset=45)
