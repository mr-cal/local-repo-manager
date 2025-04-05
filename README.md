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

commands:
  {plan,apply,update}
    plan               Create a plan
    apply              Apply a plan
    update             Create or update a config file
    
options:
  -h, --help            show this help message and exit
  --config-file CONFIG_FILE
                        path to config file (default: ~/.config/local-repo-manager/config.toml)
  --repo-dir REPO_DIR   path to parent directory of git repos (default: ~/dev)
  --verbose             enable verbose output
```

local-repo-manager assumes a two-layer filetree for repo management:
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
local-repo-manager update
```

This will create a new config file with a list of repos.

To see what changes will be made:
```bash
local-repo-manager plan
```

To apply the changes:
```bash
local-repo-manager apply
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
[project."work.craft-store"]
group = "work"
name = "craft-store"
envrc = true
[project."work.craft-store".remotes]
mr-cal = "git@github.com:mr-cal/craft-store.git"
origin = "git@github.com:canonical/craft-store.git"
```

#### project.\<group>.\<name>

The name of the local repository.

#### group

The subdirectory where the repo is organized under, such as `work` or `personal`.

#### name

The name of the repository.

#### project.\<group>.\<name>.remotes

A mapping of remote names to URLs.

#### envrc

Whether the project has an `.envrc` file to source a venv in `.venv/`.
