import logging
import os
import pathlib
import subprocess

logger = logging.getLogger(__name__)


def run_command(
    command: list[str], raise_err: bool = False, cwd: pathlib.Path | None = None
):
    logger.debug("Running command: %s", " ".join(command))
    try:
        result = subprocess.run(
            command, check=True, text=True, capture_output=True, cwd=cwd
        ).stdout.strip()
        logger.debug("Command output: %s", result)
        return result
    except subprocess.CalledProcessError as e:
        logger.debug("Error running command:")
        logger.debug("  return code: %s", e.returncode)
        logger.debug("  stdout: %s", e.stdout)
        logger.debug("  stderr: %s", e.stderr)
        if raise_err:
            raise e
        exit(os.EX_OSERR)


def is_inited(directory: pathlib.Path) -> bool:
    return (directory / ".git").is_dir()


def create_parent_dir(directory: pathlib.Path):
    parent_dir = directory.parent
    logger.debug("  creating directory %r", str(parent_dir))
    parent_dir.mkdir(parents=True, exist_ok=True)


def dir_exists(directory: pathlib.Path) -> bool:
    return directory.is_dir()
