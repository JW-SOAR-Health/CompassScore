"""
This module contains the functions to calculate the score for the state of mind.
"""

from typing import List
from shared_db.models.answer_group import AnswerGroup
from .general_score import calculate_general_score


def calculate_state_of_mind_score(answer_groups: List[AnswerGroup]) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects.
    """
    return calculate_general_score(answer_groups, scale_factor=55 / 35, offset=45)
