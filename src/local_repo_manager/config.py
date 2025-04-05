import os
import pathlib
from typing import Any

import tomlkit


def load_config(config_path: pathlib.Path) -> tomlkit.TOMLDocument | None:
    """Read a local file named config.toml and parse it as a dict."""
    try:
        return tomlkit.parse(config_path.read_text())
    except FileNotFoundError:
        print("Warning: Config file not found.")
    except Exception as e:
        print(f"Error reading config file: {e}")
        exit(os.EX_DATAERR)


def get_projects(config: tomlkit.TOMLDocument):
    projects: dict[str, Any] = config.get("project")
    if not projects:
        print("No projects found in config.")
        exit(os.EX_DATAERR)
    return projects


def get_repo_dir(
    config: tomlkit.TOMLDocument | None, arg_repo_dir: pathlib.Path
) -> pathlib.Path:
    if config:
        repo_dir_table = config.get("repo-dir")
        if repo_dir_table:
            repo_dir = pathlib.Path(repo_dir_table.get("repo-dir"))
        else:
            repo_dir = arg_repo_dir
    else:
        repo_dir = arg_repo_dir

    repo_dir.resolve()
    return repo_dir
