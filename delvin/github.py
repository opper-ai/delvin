import asyncio
import os
import subprocess


async def clone_or_reset_repo(
    repo_url: str, commit_hash: str, destination: str
) -> None:
    await clone_repo_at_commit(repo_url, commit_hash, destination)

    print("Successfully reset the repository to the latest commit.")


async def clone_repo(repo_url: str, destination_folder: str, erase=False) -> None:
    """
    Clones a GitHub repository into a given folder. If the folder already exists and is a valid git repository,
    it will not clone again unless 'erase' is True, in which case it will first remove the existing directory.

    Parameters:
    - repo_url (str): The URL of the GitHub repository to clone.
    - destination_folder (str): The local folder where the repository should be cloned.
    - erase (bool): Whether to erase the destination folder if it exists. Defaults to False.

    Returns:
    None
    """
    if erase and os.path.exists(destination_folder):
        await asyncio.create_subprocess_shell(f"rm -rf {destination_folder}")

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    clone_cmd = f"git clone git@github.com:{repo_url} {destination_folder}"
    check_git_cmd = f"git -C {destination_folder} rev-parse"
    process = await asyncio.create_subprocess_shell(
        check_git_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and not erase:
        print(
            f"Destination folder {destination_folder} already exists and is a valid git repository. Not cloning."
        )
    else:
        print(f"Cloning repository into {destination_folder}. Command: {clone_cmd}")
        process = await asyncio.create_subprocess_shell(clone_cmd)
        await (
            process.communicate()
        )  # This line ensures the script waits for the clone to complete


async def clone_repo_at_commit(
    repo_url: str, commit_hash: str, destination_folder: str
) -> None:
    """
    Clones a GitHub repository at a specific commit hash into a given folder.

    Parameters:
    - repo_url (str): The URL of the GitHub repository to clone.
    - commit_hash (str): The specific commit hash to checkout after cloning.
    - destination_folder (str): The local folder where the repository should be cloned.

    Returns:
    None
    """
    try:
        await clone_repo(repo_url, destination_folder)

        # Clean it all

        subprocess.run(
            ["git", "-C", destination_folder, "checkout", "--", "."], check=True
        )
        subprocess.run(["git", "-C", destination_folder, "clean", "-fdx"], check=True)
    except Exception as e:
        print(f"Error cloning repository: {e}\n\nWill try to reset the repository.")
        await clone_repo(repo_url, destination_folder, erase=True)
    # Checkout the specific commit
    checkout_cmd = f"git -C {destination_folder} checkout {commit_hash}"
    await asyncio.create_subprocess_shell(checkout_cmd)


def get_diff(destination_folder: str) -> str:
    """Returns the output of git diff for the given repository."""

    os.chdir(destination_folder)
    diff_cmd = "git diff"
    diff_output = subprocess.run(diff_cmd, check=True, shell=True, capture_output=True)
    return diff_output.stdout.decode("utf-8")
