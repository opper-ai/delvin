import asyncio
import os
from typing import Tuple

from opperai import AsyncClient, start_span
from opperai.types import SpanMetric

from delvin import Entry
from delvin.agent.agent import Agent
from delvin.agent.functions import grade_diffs
from delvin.github import clone_or_reset_repo, get_diff
from delvin.predictions import (
    evaluate_fix,
    get_prediction,
    meta_evaluation,
    save_prediction,
)


async def setup_agent(
    entry: Entry, predictions_directory: str, working_dir=str, overwrite: bool = False
) -> Agent:
    prediction = get_prediction(entry.instance_id, predictions_directory)
    if prediction and not overwrite:
        print(f"Prediction found for {entry.instance_id}. Skipping...")
        return None
    else:
        print(f"Prediction not found for {entry.instance_id}. Fixing...")

    agent = Agent(
        path=working_dir,
        other_info=entry.hints_text,
        problem_statement=entry.problem_statement,
        evaluate=True,
        instance_id=entry.instance_id,
    )
    return agent


async def agent_fix(
    entry: Entry,
    root_path: str,
    overwrite: bool = False,
) -> Tuple[str, Agent]:
    destination = f"{root_path}/entries/{entry.instance_id}/0/{entry.repo}"
    agent = await setup_agent(
        entry, f"{root_path}/predictions", destination, overwrite=overwrite
    )
    if agent is None:
        return (None, None)

    await clone_or_reset_repo(entry.repo, entry.base_commit, destination)
    success = await agent.go(max_steps=30)
    if success:
        diff = get_diff(agent.path)
        return (diff, agent)
    return ("", agent)


async def fix(
    entry: Entry,
    root_path: str,
    overwrite: bool = False,
) -> str:
    print("=============================================================")
    print(
        f"Fixing {entry.instance_id} on repo {entry.repo} at commit {entry.base_commit}"
    )
    client = AsyncClient()

    with start_span(
        "fix",
        entry.problem_statement,
        {
            "instance_id": entry.instance_id,
            "repo": entry.repo,
            "commit": entry.base_commit,
        },
    ) as span:
        diff, agent = await agent_fix(entry, root_path, overwrite=overwrite)
        if diff is None:
            return None
        print(f"Saving diff:\n{diff}")
        span.output = diff
        solution_diff = diff
        evaluation = await evaluate_fix(
            entry.problem_statement, solution_diff, entry.patch, entry.test_patch
        )
        print(evaluation)
        meta_eval = await meta_evaluation(
            trajectory=agent.trajectory,
            problem=entry.problem_statement,
            gold_diff=entry.patch,
        )
        save_prediction(
            path=f"{root_path}/predictions",
            instance_id=entry.instance_id,
            prediction=diff,
            model_name="delvin",
            evaluation=evaluation,
            meta_evaluation=meta_eval,
        )
        solution_diff = diff
        await client.spans.save_metric(
            span.span_uuid,
            SpanMetric(dimension="correct", score=1 if evaluation.correct else 0),
        )
        await client.spans.save_metric(
            span.span_uuid,
            SpanMetric(dimension="pass_tests", score=1 if evaluation.pass_tests else 0),
        )
        await client.spans.save_metric(
            span.span_uuid,
            SpanMetric(
                dimension="eval_score",
                score=float(evaluation.score) / 10,
                comment=evaluation.observations,
            ),
        )

    return solution_diff


def init_predictions_folder(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)
    predictions_file_path = os.path.join(path, "predictions.json")
    if not os.path.exists(predictions_file_path):
        with open(predictions_file_path, "w") as predictions_file:
            predictions_file.write("[]")
