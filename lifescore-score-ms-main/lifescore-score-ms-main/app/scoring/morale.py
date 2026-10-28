"""
This module contains the functions to calculate the score for morale.
"""

from typing import List
from shared_db.models.answer_group import AnswerGroup
from .general_score import calculate_general_score


def calculate_morale_score(answer_groups: List[AnswerGroup]) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects for the morale domain.

    Args:
        answer_groups (List[AnswerGroup]): A list of AnswerGroup objects.

    Returns:
        float: The calculated morale score.
    """
    return calculate_general_score(answer_groups, scale_factor=55 / 30, offset=45)
