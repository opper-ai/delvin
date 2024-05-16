import asyncio
import os

from delvin.agent.actions import Edit, Edits
from delvin.agent.functions import smart_code_replace


async def edit_full_rewrite(root_path: str, edit: Edit) -> str:
    file_path = os.path.join(root_path, edit.file_path)
    if not os.path.exists(file_path):
        raise ValueError(f"Error: File does not exist - {file_path}")
    with open(file_path, "r") as file:
        lines = file.readlines()

    code_to_replace_line_count = edit.code_to_replace.count("\n")

    if (
        code_to_replace_line_count != edit.end_line - edit.start_line
        and code_to_replace_line_count != edit.end_line - edit.start_line + 1
    ):
        raise ValueError(
            f"Code to replace does not match the number of lines to replace: the code to replace you provided has {code_to_replace_line_count} lines, but you specified you wanted to replace lines from {edit.start_line} to {edit.end_line} =  {edit.end_line - edit.start_line} lines to replace. Make sure to provide all lines that will be replaced."
        )

    start_index = edit.start_line - 1
    end_index = edit.end_line
    padding_lines = 5

    to_edit = "".join(lines[start_index - padding_lines : end_index + padding_lines])

    new_lines = await smart_code_replace(to_edit, edit.code_to_replace, edit.new_code)

    print(
        "CODE EDIT",
    )
    print("".join(to_edit))
    print("To replace")
    print(edit.code_to_replace)
    print("New code")
    print(edit.new_code)
    print("New lines")
    print("".join(new_lines))

    new_content = (
        "".join(lines[: start_index - padding_lines])
        + new_lines
        + "".join(lines[end_index + padding_lines :])
    )

    with open(file_path, "w") as file:
        file.write(new_content)

    return new_content


async def checkout_file(root_path: str, path: str):
    checkout_command = f"git checkout -- {path}"
    checkout_process = await asyncio.create_subprocess_shell(
        checkout_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=root_path,
    )
    checkout_stdout, checkout_stderr = await checkout_process.communicate()
    if checkout_process.returncode != 0:
        raise ValueError(
            f"Error checking out file: {checkout_stderr.decode().strip()} {checkout_stdout.decode().strip()}"
        )


async def apply_diff(root_path: str, file_path: str, diff_file_path: str) -> str:
    """Apply a diff to a file in the repository."""

    await checkout_file(root_path, file_path)
    diff_command = f"git -C {root_path} apply {diff_file_path}"
    diff_process = await asyncio.create_subprocess_shell(
        diff_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    diff_stdout, diff_stderr = await diff_process.communicate()
    if diff_process.returncode != 0:
        raise ValueError(
            f"Error applying diff: {diff_stderr.decode().strip()} {diff_stdout.decode().strip()}"
        )
    return diff_stdout.decode().strip()


async def edit_file(root_path: str, edit: Edit) -> str:
    """Edit a file in the repository."""

    file_path = os.path.join(root_path, edit.file_path)
    if not os.path.exists(file_path):
        raise ValueError(f"Error: File does not exist - {file_path}")

    edited = await edit_full_rewrite(root_path, edit)

    # Now the diff was fixed. Let's see if it makes sense...
    try:
        await lint_file(file_path)
    except Exception as e:
        # Clean up the file to edit
        await checkout_file(root_path, edit.file_path)
        raise ValueError(
            f"Error linting file.: \n{e}\n\nMake sure to use existing variables and functions in the code."
        )

    return edited


async def lint_file(file_path: str) -> str:
    """Lint a file using the ruff linter."""
    ruff_command = f"ruff check --select F821 {file_path}"
    ruff_process = await asyncio.create_subprocess_shell(
        ruff_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    ruff_stdout, ruff_stderr = await ruff_process.communicate()
    if ruff_process.returncode != 0:
        raise ValueError(
            f"Linter returned error: {ruff_stderr.decode().strip()} {ruff_stdout.decode().strip()}"
        )
    return ""


async def edit_files(root_path: str, edits: Edits) -> str:
    """Edit a file in the repository."""
    try:
        for edit in edits.edits:
            await edit_file(root_path, edit)

    except Exception as e:
        return f"Error applying edits to file {edit.file_path}: {str(e)}"

    return "Edits applied successfully"
