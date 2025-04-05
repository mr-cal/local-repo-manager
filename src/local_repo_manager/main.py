import logging
import os
import pathlib
from typing import Any

from rich import print as rprint

from . import cli, config, project, update

logger = logging.getLogger(__name__)


def run(
    projects: dict[str, Any],
    repo_dir: pathlib.Path,
    action: str,
    skip_fetch: bool = False,
):
    for name, prj in projects.items():
        prj = project.Project(prj, repo_dir, action, skip_fetch)
        if action == "apply":
            rprint(f"[bold underline]Applying plan for {name}:[/bold underline]")
        plan = prj.run()
        if action == "plan" and plan:
            rprint(f"[bold yellow]🚧 Plan for {name}:[/bold yellow]")
            for item in plan:
                rprint(item)
        else:
            rprint(f"[bold green]✅ no changes to {name}[/bold green]")


def main():
    parser = cli.setup_parser()
    args = parser.parse_args()
    cli.setup_logging(verbose=args.verbose)
    cfg = config.load_config(config_path=args.config_file)
    repo_dir = config.get_repo_dir(cfg, args.repo_dir)

    if args.command == "update":
        new_config = update.update_config(config=cfg, repo_dir=repo_dir)
        update.write_config_file(config=new_config, config_path=args.config_file)
    elif args.command in ["plan", "apply"]:
        if not cfg:
            rprint("[bold red]  ❌ no config found[/bold red]")
            exit(os.EX_DATAERR)
        projects = config.get_projects(cfg)
        run(
            projects=projects,
            repo_dir=repo_dir,
            action=args.command,
            skip_fetch=args.skip_fetch,
        )
    else:
        parser.print_help()
        exit(os.EX_USAGE)


if __name__ == "__main__":
    main()
