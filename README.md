# local-repo-manager

local-repo-manager is a utility for managing local repositories. It provides a
command-line interface, config-driven changes, and terraform-like planning and applying.

## Installation

You can install it with:

```bash
git clone https://github.com/mr-cal/local-repo-manager.git
cd local-repo-manager
uv tool install local-repo-manager
```

## Usage

```
usage: local-repo-manager plan [-h] [--config-file CONFIG_FILE] [--repo-dir REPO_DIR] [--verbose]

options:
  -h, --help            show this help message and exit
  --config-file CONFIG_FILE
                        path to config file (default: ~/.config/local-repo-manager/config.toml)
  --repo-dir REPO_DIR   path to parent directory of git repos (default: ~/dev)
  --verbose             enable verbose output
```

local-repo-manager assumes a two-layer structure for repo management:
```
.
└── dev
    ├── work
    │   ├── repo1
    │   └── repo2
    └── personal
        ├── repo3
        └── repo4
```

To generate a config file, run:
```bash
local-repo-manager update --repo-dir <path-to-repo-dir>
```

This will create a new config file with a list of repos.

To see what changes will be made:
```bash
local-repo-manager plan --repo-dir <path-to-repo-dir>
```

To apply the changes:
```bash
local-repo-manager apply --repo-dir <path-to-repo-dir>
```

## Configuration

### repo-dir

This configures where the tool will look for repositories.
```toml
[repo-dir]
repo-dir = "<path-to-repo-directory>"
```

### project

```toml
[project.snapcraft]
remotes = ["mr-cal", "lengau"]
group = "craft"
org = "canonical"
envrc = true
```

#### project.<project-name>

The name of the repo in the remote and the local directory.

#### remotes

A list of remotes. `origin` is impicitly added to the list.

#### group

The subdirectory where the repo is organized under, such as `work` or `personal`.

#### org

The owner of the repo. This determines the remote url of the origin.

#### envrc

Whether the project has an `.envrc` file to source a venv in `.venv`.
