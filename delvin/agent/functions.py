from typing import Optional

from opperai import fn

from pydantic import BaseModel, Field

from .actions import Action, Trajectory


class Evaluation(BaseModel):
    """
    Evaluation of the action an agent is going to take given its trajectory.
    """

    observations: str = Field(
        ...,
        description="Detailed observations of where we are and if the action makes sense.",
    )
    right_track: bool = Field(
        ..., description="Whether the action is on the right track."
    )
    feedback: Optional[str] = Field(
        None,
        description="Feedback for the agent if not on the right track. Could be used to course correct.",
    )


@fn
async def evaluate_action(
    trajectory: Trajectory,
    action_to_evaluate: Action,
    possible_actions: str,
    problem: str,
) -> Evaluation:
    """
    Evaluate the action an agent is going to take given its trajectory and the actions it can take.
    You are given the problem it is trying to solve.
    Be very diligent in evaluating the action, especially if it is an edit.
    You can only affect the action that is being evaluated, not the trajectory. Focus on whether the action makes sense and propose
    an alternative if it doesn't.
    """


@fn
async def smart_code_replace(code_snippet: str, to_replace: str, new_code: str) -> str:
    """
    Given a code snippet, replace the code given in the to_replace variable with the new_code variable and return the fully edited code.

    It is possible that there are slight indentation issues and small mistakes in the provided to_replace and new_code variables.
    Return a fully syntactically correct code snippet. Focus on indentation, it might be incorrect.
    """
