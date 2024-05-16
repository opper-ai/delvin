import json
import os
from typing import Optional

from opperai import fn
from pydantic import BaseModel, ConfigDict, Field

from delvin.agent.actions import Trajectory


class DiffEvaluation(BaseModel):
    observations: str = Field(
        ...,
        description="Detailed observations about the fix and what went wrong if it is incorrect. Focus on whether it would pass the tests.",
    )
    score: int = Field(
        ..., ge=0, le=10, description="How close are we to the correct solution?"
    )
    pass_tests: bool = Field(
        ...,
        description="Would the proposed fix pass the tests introduced in the test patch? It is possible that a non complete fix would pass the tests.",
    )
    correct: bool = Field(..., description="Is the proposed fix correct?")


@fn
async def evaluate_fix(
    problem: str, proposed_diff: str, gold_diff: str, test_patch: str
) -> DiffEvaluation:
    """
    Given a problem statement from a github issue and a proposed diff to fix it,
    evaluate the diff against the gold diff that was written by a human along the test_patch diff and accepted
    The goal is to assess whether the proposed fix is correct or not and would pass the new tests. If not provide
    feedback on what is wrong with the proposed fix.
    """


class MetaEvaluation(BaseModel):
    observations: str = Field(
        ...,
        description="Your detailed observation about the agent trajectory and where it did well or went wrong. Identify key steps.",
    )
    feedback: str = Field(
        ...,
        description="What would you change in order to make the agent perform better? What are the key areas of improvement?",
    )


class Prediction(BaseModel):
    instance_id: str
    model_name_or_path: str
    model_patch: str
    evaluation: Optional[DiffEvaluation] = None

    model_config = ConfigDict(protected_namespaces=())


def get_prediction(instance_id: str, path: str) -> Optional[Prediction]:
    predictions_file_path = os.path.join(path, "predictions.json")
    with open(predictions_file_path, "r") as predictions_file:
        predictions = json.load(predictions_file)
    for prediction in predictions:
        if prediction["instance_id"] == instance_id:
            return Prediction(**prediction)
    return None


@fn
async def meta_evaluation(
    trajectory: Trajectory, problem: str, gold_diff: str
) -> MetaEvaluation:
    """
    You are given the trajectory of a bug fixing software agent on a given problem, as well as a gold diff that was used by a human to fix the issue.
    Your job is to evaluate the agent's trajectory and identify the key steps where it did well or went wrong.
    """


def save_prediction(
    path: str,
    instance_id: str,
    prediction: str,
    model_name: str = "delvin",
    evaluation: DiffEvaluation = None,
    meta_evaluation: Optional[MetaEvaluation] = None,
) -> None:
    predictions_file_path = os.path.join(path, "predictions.json")
    with open(predictions_file_path, "r") as predictions_file:
        predictions = json.load(predictions_file)

    pred = {
        "instance_id": instance_id,
        "model_name_or_path": model_name,
        "model_patch": prediction,
    }
    if evaluation:
        pred["evaluation"] = evaluation.model_dump()
        pred["meta_evaluation"] = meta_evaluation.model_dump()
    for existing_pred in predictions:
        if pred["instance_id"] == existing_pred["instance_id"]:
            existing_pred.update(pred)
            break
    else:
        predictions.append(pred)
    with open(predictions_file_path, "w") as predictions_file:
        json.dump(predictions, predictions_file)
