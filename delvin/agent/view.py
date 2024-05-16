import os

from .actions import (
    ViewFile,
)


def view_file_outline(file_path: str) -> str:
    """
    Given a python file, return a formatted string that includes the total line count on top,
    followed by an outline of functions or classes in the file with their line numbers,
    accounting for possible indentation.
    """
    outlines = []
    total_lines = 0
    with open(file_path, "r") as file:
        for i, line in enumerate(file, 1):
            total_lines += 1
            stripped_line = line.strip()
            if stripped_line.startswith("def ") or stripped_line.startswith("class "):
                outlines.append(f"{i}: {stripped_line}")
    outline_str = f"Total Lines: {total_lines}\n\n# Outline:\n\n" + "\n".join(outlines)
    return outline_str


async def view_file(root_path: str, view_file_input: ViewFile) -> str:
    """View a file in the repository."""
    print("view_file_input", view_file_input)
    file_path = os.path.join(root_path, view_file_input.file_path)
    try:
        outline = view_file_outline(file_path)
        with open(file_path, "r") as file:
            all_lines = file.readlines()
            start = max(0, view_file_input.cursor_line - view_file_input.before)
            end = min(
                len(all_lines), view_file_input.cursor_line + view_file_input.after
            )
            if start > len(all_lines):
                return f"Incorrect line number: {view_file_input.cursor_line}. The file has only {len(all_lines)} lines."
            file_contents = "".join(
                f"{index + start + 1}| {line}"
                for index, line in enumerate(all_lines[start:end])
            )
        return f"{view_file_input.file_path}:\n\n{outline}\n\n# File content:\n{file_contents}"
    except FileNotFoundError:
        return f"File not found: {view_file_input.file_path}"
