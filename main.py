import argparse
import asyncio
import os

from datasets import load_dataset

from delvin import Entry
from delvin.fix import (
    fix,
    init_predictions_folder,
)

os.environ["OPPER_PROJECT"] = "delvin"
os.environ["OPPER_DEFAULT_MODEL"] = "openai/gpt-4o"

# Set up command line arguments
parser = argparse.ArgumentParser(
    description="Run the fixing process with custom parameters."
)
parser.add_argument(
    "--root_path",
    type=str,
    default="/tmp/delvin",
    help="Root path for storing predictions",
)
parser.add_argument(
    "--dataset_name",
    type=str,
    default="princeton-nlp/SWE-bench_Lite",
    help="Name of the dataset to load",
)
parser.add_argument("--split", type=str, default="dev", help="Dataset split to use")

args = parser.parse_args()

root_path = args.root_path
predictions_directory = f"{root_path}/predictions"


def get_entry(dataset, index, split="dev"):
    raw = dataset[split][index]
    return Entry(
        repo=raw["repo"],
        base_commit=raw["base_commit"],
        problem_statement=raw["problem_statement"],
        hints_text=raw["hints_text"],
        instance_id=raw["instance_id"],
        test_patch=raw["test_patch"],
        patch=raw["patch"],
    )


async def fix_entries(
    dataset, split="dev", indices=None, batch_size=3, overwrite=False
):
    if not indices:
        indices = range(len(dataset[split]))

    async def process_entry(index):
        print(f"=======Fixing entry {index}=========")
        try:
            await fix(
                get_entry(dataset, index, split),
                root_path,
                overwrite=overwrite,
            )
        except Exception as e:
            print(f"Error fixing entry {index}: {e}")
        print(f"=======Done entry {index}=========")

    tasks = [process_entry(index) for index in indices]
    semaphore = asyncio.Semaphore(batch_size)

    async def sem_task(task):
        async with semaphore:
            await task

    await asyncio.gather(*(sem_task(task) for task in tasks))


async def main():
    init_predictions_folder(predictions_directory)
    dataset = load_dataset(args.dataset_name)
    await fix_entries(dataset, args.split, overwrite=False, batch_size=25)


asyncio.run(main())
