import logging
import pathlib
import subprocess

from rich import print as rprint

from . import envrc, util

logger = logging.getLogger(__name__)


class Project:
    def __init__(
        self,
        data: dict[str, str | list[str]],
        repo_dir: pathlib.Path,
        action: str,
        skip_fetch: bool = False,
    ):
        self.name: str = data["name"]
        self.group: str = data["group"]
        self.envrc: bool = data.get("envrc", False)
        self.remotes: dict[str, str] = data.get("remotes", {})
        self.dir: pathlib.Path = (repo_dir / self.group / self.name).resolve()
        self.skip_fetch: bool = skip_fetch
        self.apply: bool = action == "apply"
        self.plan = []

    def run(self) -> list[str]:
        logger.debug("  inspecting %r", str(self.dir))
        if not util.dir_exists(self.dir):
            if self.apply:
                util.create_parent_dir(self.dir)
                self.clone_repo()
            else:
                self.plan.append(
                    f"[bold yellow]   will clone {self.name!r} in a new directory[/bold yellow]"
                )
                return self.plan
        logger.debug("  Directory exists: %s", self.dir)

        if not util.is_inited(self.dir):
            if self.apply:
                self.init_repo()
            else:
                self.plan.append(
                    f"[bold yellow]   will clone {self.name!r} in an existing dir[/bold yellow]"
                )
                return self.plan
        logger.debug("  Repo is initialized: %s", util.is_inited(self.dir))

        if self.envrc:
            self.setup_envrc()
            self.setup_venv()

        for remote_name, remote_url in self.remotes.items():
            self.set_up_remote(remote_name, remote_url)
        if self.apply and not self.skip_fetch:
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

        if envrc.is_envrc_setup(self.dir):
            logger.debug("  .envrc is already set up")
        else:
            if self.apply:
                print("  ⌛ allowing .envrc")
                util.run_command(["direnv", "allow", str(self.dir)])
                rprint("[bold green]  ✅ allowed .envrc[/bold green]")
            else:
                self.plan.append(
                    f"[bold yellow]   will allow .envrc in {self.name!r}[/bold yellow]"
                )

    def setup_venv(self) -> None:
        venv_dir = self.dir / ".venv"
        if not venv_dir.exists():
            if self.apply:
                print("  ⌛ creating venv")
                util.run_command(["uv", "venv", ".venv"], cwd=self.dir)
                rprint("[bold green]  ✅ created venv[/bold green]")
            else:
                self.plan.append(
                    f"[bold yellow]   will create venv in {self.name!r}[/bold yellow]"
                )
        else:
            logger.debug("  venv already exists: %s", str(venv_dir))

    def setup_origin(self):
        if "origin" in self.remotes:
            print("  ⌛ fetching origin")
            util.run_command(["git", "-C", str(self.dir), "fetch", "origin"])
            rprint("[bold green]  ✅ fetched origin[/bold green]")
            print("  ⌛ updating submodules")
            util.run_command(
                [
                    "git",
                    "-C",
                    str(self.dir),
                    "submodule",
                    "update",
                    "--init",
                    "--recursive",
                ]
            )
            rprint("[bold green]  ✅ updated submodules[/bold green]")
        else:
            logger.debug("  No origin remote found, skipping fetch")

    def set_up_remote(self, name: str, url: str) -> None:
        actual_url = self.get_remote_url(name)

        if actual_url is None:
            if self.apply:
                self.add_remote(name, url)
            else:
                self.plan.append(
                    f"[bold yellow]   will add remote {name!r} at {url}[/bold yellow]"
                )
        elif actual_url == url:
            logger.debug("  Url %s is correct for %s", url, name)
        else:
            if self.apply:
                self.update_remote(name, actual_url, url)
            else:
                self.plan.append(
                    f"[bold yellow]   will update url for existing remote {name!r}[/bold yellow]"
                )
                self.plan.append(
                    f"[yellow italic]    from {actual_url} [/yellow italic]"
                )
                self.plan.append(f"[yellow italic]    to   {url}[/yellow italic]")

    def add_remote(self, name: str, url: str):
        print(f"  ⌛ adding remote {self.name!r}")
        util.run_command(["git", "-C", str(self.dir), "remote", "add", name, url])
        rprint(f"[bold green]  ✅ added remote {name!r}[/bold green]")

    def update_remote(self, name: str, old_url: str, new_url: str):
        print(f"  ⌛ updating remote {self.name!r}")
        util.run_command(
            ["git", "-C", str(self.dir), "remote", "set-url", name, new_url]
        )
        rprint(f"[bold green]  ✅ updated remote {name!r}[/bold green]")
        rprint(f"[italic green]     from {old_url}[/italic green]")
        rprint(f"[italic green]     to   {new_url}[/italic green]")

    def clone_repo(self):
        print(f"  ⌛ cloning {self.name!r}")
        url = self.remotes.get("origin")
        util.run_command(["git", "clone", url, str(self.dir)])
        rprint(f"[bold green]  ✅ cloned {self.name!r}[/bold green]")

    def get_remote_url(self, remote: str) -> str | None:
        try:
            return util.run_command(
                ["git", "-C", str(self.dir), "remote", "get-url", remote],
                raise_err=True,
            )
        # remote doesn't exist
        except subprocess.CalledProcessError:
            return None

    def init_repo(self):
        print(f"  ⌛ initializing {self.name!r}")
        util.run_command(["git", "init", str(self.dir)])
        rprint(f"[bold green]  ✅ initialized {self.name!r}[/bold green]")
