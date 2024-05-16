import asyncio
import os
from typing import Tuple

from delvin.agent.actions import RunFile


async def run_file(root_path: str, run_file_input: RunFile) -> str:
    """Run a file in the repository."""
    file_path = os.path.join(root_path, run_file_input.file_path)
    run_command = f"python {file_path}"
    run_process = await asyncio.create_subprocess_shell(
        run_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    run_stdout, run_stderr = await run_process.communicate()
    return f"stdout:\n{run_stdout.decode().strip()}\nstderr:\n{run_stderr.decode().strip()}"
