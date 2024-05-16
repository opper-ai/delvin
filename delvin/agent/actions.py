from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class Search(BaseModel):
    """Search for a regex in the repository. Will search through file names and their contents."""

    regex: str = Field(
        ...,
        description="Regex to search for. Matches will be returned",
    )

    def __str__(self):
        return f"Searching for {self.regex}"


class ViewFile(BaseModel):
    """View a file in the repository. Don't hesitate to call this action multiple times to move around the file and to get more context."""

    file_path: str
    cursor_line: int = Field(
        ...,
        description="The line number to start from.",
    )
    before: int = Field(
        ge=100,
        description="Number of lines to display before the cursor line.",
    )
    after: int = Field(
        ge=100,
        description="Number of lines to display after the cursor line.",
    )

    def __str__(self):
        return f"Viewing {self.file_path} from {self.cursor_line-self.before} |{self.cursor_line}| {self.cursor_line+self.after}."


class RunFile(BaseModel):
    """Run a file in the repository with the python command"""

    file_path: str = Field(..., description="Path of the python file to run.")

    def __str__(self):
        return f"Running {self.file_path}"


class CreateFile(BaseModel):
    """Create a new file in the repository."""

    file_path: str = Field(..., description="Path of the file to create.")
    contents: str = Field(
        ...,
        description="The contents of the file to create.",
    )

    def __str__(self):
        return f"Creating {self.file_path} with contents:\n{self.contents}"


class Edit(BaseModel):
    """
    Edit a file in the repository by replacing a code block.
    Before applying edits, validate the existence and correct implementation of any new functions or variables introduced.
    Make sure you have seen all the code necessary to make the edit. View entire function bodies first.
    The edited code CANNOT refer to unknown variables or functions. NO TODOS or placeholders.
    Edits can only be done in files and lines that have already been viewed.

    You MUST remove line numbers from the new code and keep indentation intact.
    """

    file_path: str = Field(..., description="Path of the file to edit.")
    seen_all_needed_code: bool = Field(
        ...,
        description="Have you seen all the code needed to make the edit? Did you view the entire body of the function you are about to modify? You must be SURE.",
    )
    no_other_file_viewing_needed: bool = Field(
        ...,
        description="Did you take a good look at other methods/classes in the file that were provided in the file outline? Are you sure you don't need anything else? You must be SURE.",
    )
    edit_contains_all_needed_code: bool = Field(
        ...,
        description="Will you write all the code you need to replace the old code? You must guarantee that you will not take shortcuts and be thorough.",
    )
    short_description: str = Field(
        ...,
        description="A short description of the edit where you identify the lines to edit and what to do.",
    )
    code_to_replace: str = Field(
        ...,
        description="The code that will be replaced. Keep line numbers intact.",
    )
    start_line: int = Field(
        ..., description="The index of the first line that will be replaced."
    )
    end_line: int = Field(
        ...,
        description="Line number to end editing at. All lines betwee start_line and end_line are replaced.",
    )
    new_code: str = Field(
        ...,
        description="The new code to replace the old code with, WITHOUT line numbers. Indentation MUST be correct. Keep all leading whitespaces and newlines intact. Example:'    def new_action(self):\n        pass\n'",
    )
    no_unknowns: bool = Field(
        default=False,
        description="If true, the edited code does not refer to unknown variables or functions. The edited code does not contain placeholders for future implementation.",
    )

    def __str__(self):
        return f"EDIT: {self.short_description} {self.start_line}-{self.end_line}\nREPLACE:\n{self.code_to_replace}\nWITH:\n{self.new_code}"


class Edits(BaseModel):
    """Specify a list of edits to make"""

    edits: list[Edit] = Field(..., description="List of edits to make.")

    def __str__(self):
        return "\n".join(str(edit) for edit in self.edits)


class Submit(BaseModel):
    """We have fixed the problem and written tests for it. Submit the solution."""

    done: bool


class Action(BaseModel):
    thoughts: str = Field(
        ...,
        description="Step by step reasoning about the action to take. Make sure you have viewed all the necessary code before making an edit. It's always okay to look at more code.",
    )
    learning: Optional[str] = Field(
        ...,
        description="A learned fact about the repo and issue. Could be about a specific function or a pattern in the code.",
    )
    action_name: Literal[
        "search",
        "edits",
        "submit",
        "view_file",
    ] = Field(..., description="The action to take.")
    action_input: Union[
        Search,
        Edits,
        Submit,
        ViewFile,
    ]


class ActionWithResult(BaseModel):
    action: Action
    result: str


class Trajectory(BaseModel):
    """The trajectory of the agent's actions."""

    actions: list[ActionWithResult]
    gained_knowledge: list[str] = Field(default_factory=list)
