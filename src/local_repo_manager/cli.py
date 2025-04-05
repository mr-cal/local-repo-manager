import argparse
import logging
import pathlib


def setup_parser() -> argparse.ArgumentParser:
    cmd_parser = argparse.ArgumentParser(
        prog="local-repo-manager",
        description="Manage local git repos",
    )
    subparser = cmd_parser.add_subparsers(
        title="commands", dest="command", required=True
    )

    plan_parser = subparser.add_parser(
        "plan", help="Create a plan"
    )
    add_common_args(plan_parser)

    apply_parser = subparser.add_parser(
        "apply", help="Apply a plan"
    )
    apply_parser.add_argument(
        "--skip-fetch",
        help="skip fetching remotes",
        action="store_true",
    )
    add_common_args(apply_parser)

    update = subparser.add_parser(
        "update", help="Update or create a config file"
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
        help="path to parent directory of git repos (default: ~/dev)",
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
