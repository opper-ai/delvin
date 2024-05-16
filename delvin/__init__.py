from pydantic import BaseModel


class Entry(BaseModel):
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str
    instance_id: str
    patch: str
    test_patch: str
