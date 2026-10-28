"""
This module contains the general functions to calculate scores for all domains.
"""

import math
from typing import List
from shared_db.models.answer_group import AnswerGroup
from app.shared_db.core.logging_config import get_logger

logger = get_logger(__name__)


def calculate_max_sequence(lifescore_answers):
    """
    Calculate the maximum sequence from a list of lifescore_answers.

    Args:
        lifescore_answers (list): A list of LifescoreAnswer objects.

    Returns:
        int: The maximum sequence number.
    """
    return max(
        (la.sequence for la in lifescore_answers if la.sequence is not None), default=0
    )


def calculate_weight(max_sequence, sequence, group_type):
    """
    Calculate the weight for a given lifescore_answer.

    Args:
        max_sequence (int): The maximum sequence from all lifescore_answers.
        sequence (int): The sequence of the lifescore_answer.
        group_type (str): The type of the answer group ('DAILY', 'NON_DAILY',
        or 'NON_SCORING').

    Returns:
        float: The calculated weight.
    """
    day = max_sequence - sequence
    group_type = group_type.lower()

    if group_type in ["daily", "non_scoring"]:
        weight = math.exp(-day / 5)
        return round(weight, 6)
    elif group_type == "non_daily":
        weight = math.exp(-5 * day / 365)
        return round(weight, 6)
    else:
        logger.warning(
            "Unknown group_type: %s, using daily weight calculation", group_type
        )
        weight = math.exp(-day / 5)
        return round(weight, 6)


def process_lifescore_answer(la, max_sequence, group_type):
    """
    Process a single lifescore_answer and calculate its score.

    Args:
        la (LifescoreAnswer): The lifescore_answer object to process.
        max_sequence (int): The maximum sequence from all lifescore_answers.
        group_type (str): The type of the answer group ('DAILY' or 'NON_DAILY').

    Returns:
        tuple: A tuple containing the score and the weight of the lifescore_answer.
    """
    if la.sequence is None or la.answer is None:
        logger.info("Skipping LifescoreAnswer %s", la.id)
        return 0, 0

    weight = calculate_weight(max_sequence, la.sequence, group_type)
    try:
        answer_value = float(la.answer)
        score = weight * answer_value
        logger.info(
            "Score %s, weight %s, answer %s, sequence %s, weight_score %s",
            score,
            weight,
            answer_value,
            la.sequence,
            weight * answer_value,
        )
        return score, weight
    except ValueError:
        logger.info("Could not convert '%s' for LifescoreAnswer %s", la.answer, la.id)
        return 0, 0


def process_answer_group(answer_group):
    """
    Process a single AnswerGroup and calculate its score.

    Args:
        answer_group (AnswerGroup): The AnswerGroup object to process.

    Returns:
        float: The calculated score for the AnswerGroup, weighted by the
        AnswerGroup's weight attribute.
    """
    max_sequence = calculate_max_sequence(answer_group.lifescore_answers)
    logger.info("Max sequence %s", max_sequence)
    logger.info("Answer group weight %s", answer_group.weight)
    if answer_group.weight < 0.0001:
        return 0

    total_score = 0.0
    total_weight = 0.0
    logger.info("Answer group lifescore answers %s", answer_group.lifescore_answers)
    logger.info(
        "Answer group lifescore answers len %s", len(answer_group.lifescore_answers)
    )
    for la in answer_group.lifescore_answers:
        score, weight = process_lifescore_answer(
            la, max_sequence, answer_group.group_type
        )
        total_score += score
        total_weight += weight
    if total_weight > 0:
        raw_score = total_score / total_weight
        return raw_score * answer_group.weight
    return 0


def calculate_general_score(
    answer_groups: List[AnswerGroup], scale_factor: float, offset: float
) -> float:
    """
    Calculate the score based on a list of AnswerGroup objects.

    Args:
        answer_groups (List[AnswerGroup]): A list of AnswerGroup objects.
        scale_factor (float): The factor to scale the raw score.
        offset (float): The offset to add to the scaled score.

    Returns:
        float: The calculated score. Returns 0.0 if the input list is empty.
    """
    if not answer_groups:
        return 0.000

    final_score = sum(process_answer_group(ag) for ag in answer_groups)

    final_score = (final_score * scale_factor) + offset
    rounded_score = math.ceil(final_score * 100 - 0.5) / 100
    logger.info("Final score %s", final_score)
    logger.info("Rounded score %s", rounded_score)
    return rounded_score
