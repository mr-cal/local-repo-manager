import subprocess
import os
import tomlkit
from typing import Any
import argparse
import pathlib
from rich import print as rprint
import logging
import datetime
import difflib
import shutil

logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    cmd_parser = argparse.ArgumentParser(
        prog="local-repo-manager",
        description="Manage local git repos",
    )
    subparser = cmd_parser.add_subparsers(
        title="commands", dest="command", required=True
    )

    plan_parser = subparser.add_parser(
        "plan", help="Create a plan for managing git repos"
    )
    add_common_args(plan_parser)

    apply_parser = subparser.add_parser(
        "apply", help="Apply a plan for managing git repos"
    )
    add_common_args(apply_parser)

    update = subparser.add_parser(
        "update", help="Update the config file for a directory of repos"
    )
    add_common_args(update)

    return cmd_parser


def add_common_args(subparser: argparse.ArgumentParser):
    subparser.add_argument(
        "--config-file",
        help="path to config file (default: ~/.config/local-repo-manager/config.toml)",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".config/local-repo-manager/config.toml",
    )
    subparser.add_argument(
        "--repo-dir",
        help="path to parent directory of git repos (default: ~/.config/config/repo-manager/repos)",
        type=pathlib.Path,
        default=pathlib.Path.home() / "dev",
    )
    subparser.add_argument(
        "--verbose",
        action="store_true",
        help="enable verbose output",
    )


def setup_logging(verbose: bool):
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")


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


def run(projects: dict[str, Any], repo_dir: pathlib.Path, action: str):
    for name, project in projects.items():
        project = Project(name, project, repo_dir, action)
        if action == "apply":
            rprint(f"[bold underline]Applying plan for {name}:[/bold underline]")
        plan = project.run()
        if action == "plan" and plan:
            rprint(f"[bold yellow]🚧 Plan for {name}:[/bold yellow]")
            for item in plan:
                rprint(item)
        else:
            rprint(f"[bold green]✅ no changes to {name}[/bold green]")


def create_parent_dir(directory: pathlib.Path):
    parent_dir = directory.parent
    logger.debug("  creating directory %r", str(parent_dir))
    parent_dir.mkdir(parents=True, exist_ok=True)


def dir_exists(directory: pathlib.Path) -> bool:
    return directory.is_dir()


def is_inited(directory: pathlib.Path) -> bool:
    return (directory / ".git").is_dir()


class Project:
    def __init__(
        self,
        name,
        data: dict[str, str | list[str]],
        repo_dir: pathlib.Path,
        action: str,
    ):
        self.name: str = name
        self.org: str = data["org"]
        self.group: str = data["group"]
        self.envrc: bool = data.get("envrc", False)
        self.remotes: list[str] = ["origin", *data.get("remotes", [])]
        self.dir: pathlib.Path = (repo_dir / self.group / self.name).resolve()
        self.origin_url: str = f"git@github.com:{self.org}/{self.name}.git"
        self.apply: bool = action == "apply"
        self.plan = []

    def run(self) -> list[str]:
        logger.debug(f"  inspecting %r", str(self.dir))
        if not dir_exists(self.dir):
            if self.apply:
                create_parent_dir(self.dir)
                self.clone_repo()
            else:
                self.plan.append(
                    f"[bold yellow]   will clone {self.name!r} in a new directory[/bold yellow]"
                )
                return self.plan
        logger.debug("  Directory exists: %s", self.dir)

        if not is_inited(self.dir):
            if self.apply:
                self.init_repo()
            else:
                self.plan.append(
                    f"[bold yellow]   will clone {self.name!r} in an existing dir[/bold yellow]"
                )
                return self.plan
        logger.debug("  Repo is initialized: %s", is_inited(self.dir))

        if self.envrc:
            self.setup_envrc()
            self.setup_venv()

        for remote in self.remotes:
            self.set_up_remote(remote)
        if self.apply:
            self.setup_origin()

        return self.plan

    def setup_envrc(self) -> None:
        envrc_file = self.dir / ".envrc"
        if not envrc_file.exists():
            if self.apply:
                print("  ⌛ creating .envrc")
                envrc_file.write_text("source .venv/bin/activate")
                rprint("[bold green]  ✅ created .envrc[/bold green]")
            else:
                self.plan.append(
                    f"[bold yellow]   will create .envrc in {self.name!r}[/bold yellow]"
                )
                return

        if self.is_envrc_setup():
            logger.debug("  .envrc is already set up")
        else:
            print("  ⌛ allowing .envrc")
            run_command(["direnv", "allow", str(self.dir)])
            rprint("[bold green]  ✅ allowed .envrc[/bold green]")

    def setup_venv(self) -> None:
        venv_dir = self.dir / ".venv"
        if not venv_dir.exists():
            if self.apply:
                print("  ⌛ creating venv")
                run_command(["uv", "venv", ".venv"], cwd=self.dir)
                rprint("[bold green]  ✅ created venv[/bold green]")
            else:
                self.plan.append(
                    f"[bold yellow]   will create venv in {self.name!r}[/bold yellow]"
                )
        else:
            logger.debug("  venv already exists: %s", str(venv_dir))

    def is_envrc_setup(self) -> bool:
        output = run_command(["direnv", "status"], cwd=self.dir)
        if "Found RC allowed true" in output:
            logger.debug("  .envrc is allowed")
            return True

        logger.debug("  .envrc is not allowed")
        return False

    def setup_origin(self):
        print("  ⌛ fetching origin")
        run_command(["git", "-C", str(self.dir), "fetch", "origin"])
        rprint("[bold green]  ✅ fetched origin[/bold green]")
        print("  ⌛ updating submodules")
        run_command(
            ["git", "-C", str(self.dir), "submodule", "update", "--init", "--recursive"]
        )
        rprint("[bold green]  ✅ updated submodules[/bold green]")

    def set_up_remote(self, remote: str) -> None:
        remote_url = self.get_remote_url(remote)
        actual_org = self.org if remote == "origin" else remote
        expected_url = f"git@github.com:{actual_org}/{self.name}.git"

        if remote_url is None:
            if self.apply:
                self.add_remote(remote, expected_url)
            else:
                self.plan.append(
                    f"[bold yellow]   will add remote {remote!r} at {expected_url}[/bold yellow]"
                )
        elif remote_url == expected_url:
            logger.debug("  Url %s is correct for %s", remote_url, remote)
        else:
            if self.apply:
                self.update_remote(remote, remote_url, expected_url)
            else:
                self.plan.append(
                    f"[bold yellow]   will update url for existing remote {remote!r}[/bold yellow]"
                )
                rprint(f"[yellow italic]    from {remote_url} [/yellow italic]")
                rprint(f"[yellow italic]    to   {expected_url}[/yellow italic]")

    def add_remote(self, name: str, url: str):
        print(f"  ⌛ adding remote {self.name!r}")
        run_command(["git", "-C", str(self.dir), "remote", "add", name, url])
        rprint(f"[bold green]  ✅ added remote {name!r}[/bold green]")

    def update_remote(self, name: str, old_url: str, new_url: str):
        print(f"  ⌛ updating remote {self.name!r}")
        run_command(["git", "-C", str(self.dir), "remote", "set-url", name, new_url])
        rprint(f"[bold green]  ✅ updated remote {name!r}[/bold green]")
        rprint(f"[italic green]     from {old_url}[/italic green]")
        rprint(f"[italic green]     to   {new_url}[/italic green]")

    def clone_repo(self):
        print(f"  ⌛ cloning {self.name!r}")
        run_command(["git", "clone", self.origin_url, str(self.dir)])
        rprint(f"[bold green]  ✅ cloned {self.name!r}[/bold green]")

    def get_remote_url(self, remote: str) -> str | None:
        try:
            return run_command(
                ["git", "-C", str(self.dir), "remote", "get-url", remote],
                raise_err=True,
            )
        except subprocess.CalledProcessError:
            return None

    def init_repo(self):
        print(f"  ⌛ initializing {self.name!r}")
        run_command(["git", "init", str(self.dir)])
        rprint(f"[bold green]  ✅ initialized {self.name!r}[/bold green]")


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
            if is_inited(project_dir):
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
    if config_path.exists():
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
        rprint(f"[bold green]  ✅ no changes to config[/bold green]")


def get_remotes(directory: pathlib.Path) -> list[str]:
    return run_command(
        ["git", "-C", str(directory), "remote"], raise_err=True
    ).splitlines()


def get_project_info(
    project_dir: pathlib.Path, group_dir: pathlib.Path
) -> tuple[str, dict[str, Any] | None]:
    project = dict()
    remotes = get_remotes(project_dir)
    logger.debug("    remotes: %s", remotes)
    if "origin" in remotes:
        remotes.remove("origin")
    if remotes:
        project["remotes"] = remotes
    name = project_dir.name
    project["group"] = group_dir.name
    project["org"] = get_org_name(project_dir, group_dir.name, name)
    if project["org"] is None:
        return name, None
    if has_envrc(project_dir):
        project["envrc"] = True
    logger.debug("  created project for %s: %s", name, project)
    return name, project


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


def get_org_name(project_dir: pathlib.Path, group: str, name: str) -> str | None:
    # get the org name (the owner of the origin remote)
    try:
        origin_url = run_command(
            ["git", "-C", str(project_dir), "remote", "get-url", "origin"],
            raise_err=True,
        )
        if "launchpad.net" in origin_url:
            rprint(
                f"[bold red]  ❌ ignoring {group}/{name} - launchpad.net is not a supported remote[/bold red]"
            )
            return None
        # get the second last part of the url
        return origin_url.split(":")[1].split("/")[-2]
    except subprocess.CalledProcessError:
        logger.debug("  no origin remote found for %r", str(project_dir))
        return None


def get_repo_dir(
    config: tomlkit.TOMLDocument, arg_repo_dir: pathlib.Path
) -> pathlib.Path:
    repo_dir_table = config.get("repo-dir")
    if repo_dir_table:
        repo_dir = pathlib.Path(repo_dir_table.get("repo-dir"))
    else:
        repo_dir = arg_repo_dir

    repo_dir.resolve()
    return repo_dir


def main():
    parser = setup_parser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    config = load_config(config_path=args.config_file)
    repo_dir = get_repo_dir(config, args.repo_dir)

    if args.command == "update":
        new_config = update_config(config=config, repo_dir=repo_dir)
        write_config_file(config=new_config, config_path=args.config_file)
    elif args.command in ["plan", "apply"]:
        if not config:
            rprint("[bold red]  ❌ no config found[/bold red]")
            exit(os.EX_DATAERR)
        projects = get_projects(config)
        run(projects=projects, repo_dir=repo_dir, action=args.command)
    else:
        parser.print_help()
        exit(os.EX_USAGE)


if __name__ == "__main__":
    main()
