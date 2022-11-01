#! /usr/bin/env python
"""Stage Ntuples."""
import asyncio
import csv
import logging
import os
import pathlib
from mrtools import utils

import click

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.WARNING,
)
log = logging.getLogger("stage")

SKIMS = ["Met", "MetLepEnergy", "DoubleLep"]
DEFAULT_SKIM = "Met"
PERIODS = ["Run2016preVFP", "Run2016postVFP", "Run2017", "Run2018"]
DEFAULT_PERIODS = PERIODS

EOS_URL = "root://eos.grid.vbc.ac.at"
EOS_PATH = pathlib.Path(
    "/eos/vbc/experiments/cms/store/user/liko/StopsCompressed/nanoTuples"
)
SCRATCH_PATH = pathlib.Path(
    "/scratch-cbe/users/dietrich.liko/StopsCompressed/nanoTuples"
)

MAX_STAGE = 10

XRDCP = "/groups/hephy/cms/dietrich.liko/conda/envs/mrt-root626-py310/bin/xrdcp"
XRDADLER32 = (
    "/groups/hephy/cms/dietrich.liko/conda/envs/mrt-root626-py310/bin/xrdadler32"
)

sem_stage_file = asyncio.Semaphore(MAX_STAGE)


async def xrd_checksum(name: str) -> str:
    """Wrapper xrdadler32."""
    proc = await asyncio.create_subprocess_exec(
        XRDADLER32, name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode:
        raise Exception(
            f"Return code {proc.returncode} getting remore adler32 for {name}"
        )
    return stdout.decode("UTF-8").split()[0]


async def xrd_stage(source: str, target: str) -> None:
    """Wrapper xrdcp."""

    proc = await asyncio.create_subprocess_exec(
        XRDCP,
        "--nopbar",
        "--parallel",
        "4",
        "--retry",
        "3",
        "--cksum",
        "adler32",
        "--force",
        source,
        target,
    )
    status = await proc.wait()
    if status:
        log.error(f"Return code {status} copying {source}")


async def stage_file(name: pathlib.PurePath) -> None:
    """Stage a file."""
    async with sem_stage_file:
        source = EOS_PATH / name
        target = SCRATCH_PATH / name

        if target.exists():
            try:
                chksums = await asyncio.gather(
                    xrd_checksum(f"{EOS_URL}/{source}"),
                    xrd_checksum(str(target)),
                )
                if chksums[0] != chksums[1]:
                    log.info("Checksum mismatch %s", name)
                    os.unlink(target)
                else:
                    log.info("File %s exists.", name)
                    return
            except Exception as e:
                log.error("Exception %s. File %s skipped.", e, name)
                return

        log.info("Copying %s", name)
        await xrd_stage(f"{EOS_URL}/{source}", str(target))


async def stage_all_files(skim: str, period: list[str]) -> None:
    """Stage all files."""
    file_names = []
    for p in period:
        log.info("Skim %s - Period %s", skim, p)
        file_names += get_files_from_csv(skim, p)

    await asyncio.gather(*(stage_file(f) for f in file_names))


def get_files_from_csv(skim: str, period: str) -> list[pathlib.PurePath]:
    """Read sample csv file and generate file names."""
    files = []
    sample_file = f"samples/{skim} - {period}.csv"
    with open(sample_file, "r") as csv_input:
        for e in csv.DictReader(csv_input):
            prefix = e["Path"]
            name = e["Name"]
            tag = e["Tag"]
            if prefix.startswith("#") or not tag:
                continue
            nr = int(e["#Files"])
            if nr == 1:
                files.append(pathlib.PurePath(tag, skim, name, f"{name}.root"))
            else:
                for i in range(nr):
                    files.append(pathlib.PurePath(tag, skim, name, f"{name}_{i}.root"))
    return files


@click.command()
@click.option("--skim", default=DEFAULT_SKIM, type=click.Choice(SKIMS))
@click.option(
    "--period", multiple=True, default=DEFAULT_PERIODS, type=click.Choice(PERIODS)
)
@utils.click_option_logging(log)
def main(skim: str, period: list[str]) -> None:
    """Stage Ntuples from EOS to scratch."""
    asyncio.run(stage_all_files(skim, period))


if __name__ == "__main__":
    main()
