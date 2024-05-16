import asyncio
import os
import re
from typing import cast

from opperai import fn, start_span, trace


from pydantic import BaseModel

from .actions import (
    Action,
    ActionWithResult,
    CreateFile,
    Edits,
    Search,
    Trajectory,
    ViewFile,
)
from .edit import edit_files
from .functions import evaluate_action
from .view import view_file


class Agent(BaseModel):
    """The agent that will solve the problem"""

    path: str
    problem_statement: str
    other_info: str = ""
    trajectory: Trajectory = Trajectory(actions=[])
    evaluate: bool = False
    instance_id: str = ""

    @fn()
    async def get_action(
        trajectory: Trajectory, problem: str, other_info: str
    ) -> Action:
        """
        You are a world class programmer tasked with solving the given problem as simply as possible but without taking any shortcuts.
        You can search, look at files and scroll through them, edit them, and submit the solution for review.
        You cannot run tests so you need to think step by step about whether you have done the right thing.
        You find the next action to take to fix the problem, based on the previous actions taken.

        When editing files, make sure to:
         - correct line numbers and indentation, this is where most errors occur.
         - not reference non existing code (a linter will verify edits for this)
         - NEVER add placeholders for future implementation.
         - reuse existing code when possible. You should prioritize reuse. Don't hesisate to search and scroll through files.

        Extra rules:
        - Do not open a file without confirming it exists via search first
        - Do not get stuck on file names, be ready to expand your search a bit.

        Also, do NOT refer to non existing functions or code yet to be written. If you need more data before making an edit,
        you can search for it.
        """

    async def code_search(self, regex: str) -> str:
        """Search for files with the regex in the contents, excluding directories starting with '.'.
        Return the file names along with the line number and the line where the regex appears."""
        matches = []
        compiled_regex = re.compile(regex)
        for root, _, filenames in await asyncio.to_thread(os.walk, self.path):
            if "/." in root or root.endswith("/."):
                continue  # Skip hidden directories
            for filename in filenames:
                file_path = os.path.join(root, filename)
                try:
                    with await asyncio.to_thread(
                        open, file_path, "r", encoding="utf-8", errors="ignore"
                    ) as file:
                        for line_number, line in enumerate(file, start=1):
                            if compiled_regex.search(line):
                                relative_path = os.path.relpath(file_path, self.path)
                                matches.append(
                                    f"- {relative_path} line {line_number} : {line.strip()[0:120]}"
                                )
                                if len(matches) >= 100:
                                    return "\n".join(matches)
                except Exception:
                    continue  # If there's an error opening/reading a file, skip it
        if len(matches) == 0:
            return f"No files containing '{regex}' found."
        return "\n".join(matches[:100])

    @trace
    async def edit_file(self, edit_input: Edits) -> str:
        """Edit a file in the repository."""

        return await edit_files(self.path, edit_input)

    async def create_file(self, create_input: CreateFile) -> str:
        """Create a file in the repository."""
        file_path = os.path.join(self.path, create_input.file_path)
        try:
            with open(file_path, "w") as file:
                file.write(create_input.contents)
            return f"Created file: {create_input.file_path}"
        except Exception as e:
            return f"Failed to create file: {create_input.file_path}. Error: {e}"

    async def find_files(self, regex: str) -> str:
        """Search for files matching regex string in the name, searching recursively."""
        files = []
        compiled_regex = re.compile(regex)
        # Use asyncio.to_thread to run the blocking os.walk in a separate thread
        for root, _, filenames in await asyncio.to_thread(os.walk, self.path):
            for filename in filenames:
                if compiled_regex.search(filename):
                    relative_path = os.path.relpath(
                        os.path.join(root, filename), self.path
                    )
                    files.append(f"- {relative_path}")
        if len(files) == 0:
            return f"No file names containing {regex} found."
        return "\n".join(files[:100])

    @trace
    async def string_search(self, search_input: Search) -> str:
        try:
            code_search = await self.code_search(search_input.regex)
            file_search = await self.find_files(search_input.regex)
        except Exception as e:
            return f"Error searching for regex: {search_input.regex}. Error: {e}"
        return f"First 100 files containing {search_input.regex}:\n\n{code_search}\n\nFirst 100 filenames matching {search_input.regex}:\n\n{file_search}"

    async def execute_action(self, action: Action) -> str:
        """Execute the action returned by the agent."""
        if action.action_name == "search":
            return await self.string_search(cast(Search, action.action_input))
        elif action.action_name == "edits":
            return await self.edit_file(cast(Edits, action.action_input))
        elif action.action_name == "submit":
            return "Submitted the solution."
        elif action.action_name == "create_file":
            return await self.create_file(cast(CreateFile, action.action_input))
        elif action.action_name == "view_file":
            view_file_input = cast(ViewFile, action.action_input)
            return await view_file(
                self.path,
                view_file_input,
            )
        else:
            raise ValueError(f"Unknown action: {action.action_name}")

    async def reset(self) -> None:
        """Reset the agent's state."""
        self.trajectory = Trajectory(actions=[])

    async def go(self, max_steps=1) -> bool:
        for i in range(max_steps):
            with start_span(name="step", metadata={"step": i}):
                action = await self.get_action(
                    trajectory=self.trajectory,
                    problem=self.problem_statement,
                    other_info=self.other_info,
                )
                if action.learning:
                    self.trajectory.gained_knowledge.append(action.learning)

                self.log("======================\n")
                self.log(f"Thoughts: {action.thoughts}\n\n")
                self.log(f"Action Name: {action.action_name}\n\n")
                self.log(f"Action Input:\n{action.action_input}\n\n")

                if self.evaluate:
                    evaluation = await evaluate_action(
                        trajectory=self.trajectory,
                        action=action,
                        possible_actions=Action.model_json_schema(),
                        problem=self.problem_statement,
                    )
                    if not evaluation.right_track:
                        result = "An evaluator thinks you're not on the right track:\n"
                        result += (
                            f"Here's what the he thinks:\n {evaluation.observations} \n"
                        )
                        result += f"Evaluator feedback: {evaluation.feedback}\n\n"
                        result += "Action result:\n\n"
                    else:
                        result = await self.execute_action(action)

                else:
                    result = await self.execute_action(action)
                action_with_result = ActionWithResult(action=action, result=result)
                self.trajectory.actions.append(action_with_result)

                self.log(f"Result:\n{result}")
                if action.action_name == "submit":
                    return True
        self.log("Failed to solve the problem in the given steps.")
        return False

    def log(self, message: str) -> None:
        print(f"[{self.instance_id}] {message}")
