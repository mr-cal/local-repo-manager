import datetime
import difflib
import logging
import os
import pathlib
import shutil
from typing import Any

import tomlkit
from rich import print as rprint

from . import envrc, util

logger = logging.getLogger(__name__)


def get_project_info(
    project_dir: pathlib.Path, group_dir: pathlib.Path
) -> tuple[str, dict[str, Any] | None]:
    project = dict()
    config_name = f"{group_dir.name}.{project_dir.name}"
    remotes = get_remotes(project_dir)
    if remotes:
        project["remotes"] = remotes
    else:
        # no remotes means we can't clone anything
        return config_name, None

    project["group"] = group_dir.name
    project["name"] = project_dir.name
    if envrc.has_envrc(project_dir):
        project["envrc"] = True
    logger.debug("  created project for %s: %s", config_name, project)
    return config_name, project


def get_remotes(directory: pathlib.Path) -> dict[str, str]:
    remote_names = util.run_command(
        ["git", "-C", str(directory), "remote"]
    ).splitlines()
    remotes = dict()
    for remote in remote_names:
        remote_url = util.run_command(
            ["git", "-C", str(directory), "remote", "get-url", remote]
        )
        remotes[remote] = remote_url
    return remotes


def update_config(config: tomlkit.TOMLDocument | None, repo_dir: pathlib.Path):
    """Look for existing git repos, check their remotes, update the dict, and print it as toml."""
    if not config:
        config = tomlkit.document()
        config["project"] = tomlkit.table()

    if not repo_dir.is_dir():
        rprint(f"[bold red]  ❌ repo directory {repo_dir} does not exist[/bold red]")
        exit(os.EX_NOINPUT)
    for group_dir in repo_dir.iterdir():
        logger.debug("looking for projects in %r", str(group_dir))
        for project_dir in group_dir.iterdir():
            if util.is_inited(project_dir):
                logger.debug("  found project %r", str(project_dir))
                rprint(
                    f"[bold green]  ✅ found '{group_dir.name}/{project_dir.name}'[/bold green]"
                )
                name, project = get_project_info(project_dir, group_dir)
                if project:
                    config["project"][name] = project
            else:
                rprint(
                    f"[bold yellow]  ❓ no valid git repo found in {group_dir.name}/{project_dir.name}[/bold yellow]"
                )

    return config


def write_config_file(config: tomlkit.TOMLDocument, config_path: pathlib.Path):
    # get filepath friendly timestamp (to the minute)
    if not config_path.parent.exists():
        logger.debug("  creating config directory %r", str(config_path.parent))
        config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        # check if changes were made
        existing_config = tomlkit.parse(config_path.read_text())
        if config == existing_config:
            rprint("[bold green]✅ no changes to config[/bold green]")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M")
        backup_path = config_path.parent / f".{config_path.name}.{timestamp}.bak"
        shutil.copy(config_path, backup_path)
        rprint(f"[bold green]  ✅ backed up config to {backup_path}[/bold green]")
    else:
        logger.debug("  no existing config file found, skipping backup")
        backup_path = None

    config_path.write_text(tomlkit.dumps(config))
    rprint(f"[bold green]  ✅ updated config file {config_path}[/bold green]")

    if backup_path:
        print_diff(config_path, backup_path)


def print_diff(new: pathlib.Path, old: pathlib.Path):
    new_lines = new.read_text().splitlines()
    old_lines = old.read_text().splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile=str(old), tofile=str(new), lineterm=""
    )
    if diff:
        for line in diff:
            print(line)
    else:
        rprint("[bold green]  ✅ no changes to config[/bold green]")
