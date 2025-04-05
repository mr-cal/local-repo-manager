import logging
import pathlib

from . import util

logger = logging.getLogger(__name__)


def has_envrc(directory: pathlib.Path) -> bool:
    """True if the repo has a .envrc file for activating a venv."""
    envrc_path = directory / ".envrc"
    if envrc_path.exists():
        logger.debug("  found .envrc file in %r", str(directory))
        content = envrc_path.read_text()
        if "source .venv/bin/activate" in content:
            logger.debug("  found venv .envrc file in %r", str(directory))
            return True
    return False


def is_envrc_setup(directory: pathlib.Path) -> bool:
    output = util.run_command(["direnv", "status"], cwd=directory)
    if "Found RC allowed true" in output:
        logger.debug("  .envrc is allowed")
        return True

    logger.debug("  .envrc is not allowed")
    return False
