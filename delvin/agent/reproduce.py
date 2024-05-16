from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from delvin.agent.actions import Edit, Edits, Search, Submit, ViewFile


class Action(BaseModel):
    thoughts: str = Field(
        ...,
        description="Step by step reasoning about the action to take. Make sure you have viewed all the necessary code before making an edit. It's always okay to look at more code.",
    )
    learning: Optional[str] = Field(
        ...,
        description="A useful learning that will help in the future.",
    )
    action_name: Literal[
        "search",
        "edits",
        "view_file",
    ]
    action_input: Union[
        Search,
        Edits,
        Submit,
        ViewFile,
    ]
