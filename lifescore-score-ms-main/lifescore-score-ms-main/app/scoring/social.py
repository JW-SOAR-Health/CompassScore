"""
This module contains the functions to calculate the score for social.
"""

from typing import List
from shared_db.models.answer_group import AnswerGroup
from .general_score import calculate_general_score


def calculate_social_score(answer_groups: List[AnswerGroup]) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects for the social domain.

    Args:
        answer_groups (List[AnswerGroup]): A list of AnswerGroup objects.

    Returns:
        float: The calculated social score.
    """
    return calculate_general_score(answer_groups, scale_factor=55 / 30, offset=45)
