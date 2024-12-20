# Arches Containers

## Overview

Arches Containers is a developer CLI tool to create and manage containerized Arches development environments. See [Arches](https://github.com/archesproject/arches) project for information related to the framework.

It provides commands to create and manage arches-container projects, which contain the necessary configuration files to run Arches in a containerized environment, complete with required minimum dependencies and services.

These arches-cnontainer projects can be shared with others or stored in a version control system. They can be exported to a repository folder and imported back into the workspace.

It can also be used to generate VSCode debug configurations to allow debugging code insode the containers.

It is still in the early stages of development and is subject to change, but we welcome sugestions and contributions. See the [Contributing](#contributing) section for more information.

## Installation

Throughout the documentation, the concept of a **_workspace_** is mentioned. This is the root working directory where the Arches projects and core repos sit.

It is recommended that you use a virtual environment within the workspace. The following instructions assume you are in the workspace directory.

```sh
cd /path/to/workspace
python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
```

> See the [Arches documentation](https://arches.readthedocs.io/en/stable/installing/installation/) for more information.

### From PyPI

1. Install the package:

    ```sh
    pip install arches-containers
    ```

## Build from source and publish

1. Clone the repository:

    ```sh
    cd /path/to/workspace
    git clone https://github.com/HistoricEngland/arches-containers.git
    cd arches-containers
    ```

1. Install the package:

    ```sh
    cd /path/to/arches-containers # where the pyproject.toml file is located
    pip install .[dev] 
    ```

   > The `[dev]` option installs the developer dependencies. Some terminals may not support this syntax and you'll need to use quotes instead: `pip install '.[dev]'`.

> ℹ: Documentation on how to build and publish to PyPI can be found [here](https://packaging.python.org/en/latest/guides/section-build-and-publish/).

To build the package, run the following command:

```sh
cd /path/to/arches-containers # where the pyproject.toml file is located
python -m build
```

This will create a `dist` folder with the built package.

The instuctions for publishing us [twine](https://twine.readthedocs.io/en/stable/) to upload the package to PyPI. It expects that you have a configured [`.pypirc`](https://packaging.python.org/en/latest/specifications/pypirc/) to hold your PyPI API token credentials. The file should look like this:

> ⚠️ **Do not commit this file to source control.**

```ini
[pypi]
username = __token__
password = <API token>

[testpypi]
username = __token__
password =  <API token>
```

Then run the following command to upload the package:

```sh
cd /path/to/arches-containers # where the pyproject.toml file is located
twine upload dist/*
```

For testing, you can upload to the test PyPI server by specifying the repository:

```sh
cd /path/to/arches-containers # where the pyproject.toml file is located
twine upload --repository testpypi dist/*
```

## Usage

Use the `arches-containers` command to manage arches-container projects.

> ⚠️ **arches-containers** will create a `.arches-containers` folder in the workspace directory to store project configurations. It will look for this up the file tree when running commands. Should there be another `.arches-containers` folder in the workspace directory, the CLI may not work as expected.

```sh
cd /path/to/workspace
arches-containers [OPTIONS] COMMAND [ARGS]...
```

> Note: The command is aliased as `acon` for convenience.

### Create a Project

Steps to create a new container project.

```sh
cd /path/to/workspace
arches-containers create -p <project_name> -v <version> [-o <organization>] [--activate]
```

- `-p`, `--project_name`: The name of the project. This value will be slugified to lowercase with underscore separators.
- `-v`, `--version`, `--ver`: The Arches version the project will be using (major.minor format).
- `-o`, `--organization`: The GitHub organization of the Arches repo (default: archesproject).
- `--activate`: Activate the project after creation. If it is the first project then it will be activated by default.

### Manage a Project

Steps to manage an existing container project.

```sh
cd /path/to/workspace
arches-containers manage -p <project_name> [-b] [-o <organization>] [-br <branch>] <action>
```

- `-p`, `--project_name`: The name of the project. If excluded, the active project will be used.
- `-b`, `--build`: Rebuild containers when composing up.
- `-o`, `--organization`: The GitHub organization of the Arches repo (default: archesproject).
- `-br`, `--branch`: The branch of the Arches repo to use. Default is the 'dev/[version].x' branch.
- `<action>`: Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project, 'activate' to set the project as the active project.

### List Projects

Steps to list all container projects.

```sh
cd /path/to/workspace
arches-containers list
```

### Delete a Project

Steps to delete an existing container project.

```sh
cd /path/to/workspace
arches-containers delete -p <project_name>
```

- `-p`, `--project_name`: The name of the project to delete.

### Generate Debug Config

Steps to generate a VSCode launch.json configuration for the workspace.

```sh
cd /path/to/workspace
arches-containers generate-debug-config
```

### Export a Project

The user can export an arches-container project to a repository folder. This is useful when the user wants to share the project with others or store it in a version control system. The export command will create a folder called `.ac` in the repository folder and copy the necessary files to it.

The docker compose files in the exported arches-container project will need to be run manually as the command only access those in the `.arches-containers` folder.

> TODO: In future there will a command to import a project from a repository folder so it is available to the command line.

```sh
cd /path/to/workspace
arches-containers export [-p <project_name>] [-r <repo_path>]
```

- `-p`, `--project_name`: The name of the project to export. Default is the active project.
- `-r`, `--repo_path`: The path to the repository folder. Default is `<workspace directory path>/<project_name>`.

### Import a Project

The user can import an arches-container project from a repository folder. This is useful when the user wants to use a project that has been shared with them or stored in a version control system.

```sh
arches-containers import -p <project_name> [-r <repo_path>]
```

- `-p`, `--project_name`: The name of the project to import. It will look for a folder at the path  in the repository folder.
- `-r`, `--repo_path`: OPTIONAL - Use this is the name of the repo directory does not match the pattern `<workspace_path>/<project_name>`. This path **must** contain a folder called `.ac_<project_name>`.

**example:**
Given the following directory structure:

```text
workspace
├── project1
│   ├── .ac_project1
│   └── ...
└── a_different_repo
    ├── .ac_project2
    └── ...
```

To import `project1`:

```sh
cd /path/to/workspace
arches-containers import -p project1
```

To import `project2`:

```sh
cd /path/to/workspace
arches-containers import -p project2 -r ./a_different_repo
```

## Configuration of the Project

The project is stored in a directory called `<workspace_path>/.arches-containers/<project_name>` and is compromised of a config file and a variety of files used with docker compose to stand up and environment.

The project configuration file `config.json` is used to store default values for the CLI commands when the project is activated.

**example:**

```json
{
    "project_name": "arches_her_project",
    "project_name_url_safe": "archesherproject",
    "arches_version": "7.5",
    "arches_repo_organization": "archesproject",
    "arches_repo_branch": "dev/7.5.x"
}
```

When in the project directory, there are two files that you may want to configure:

- `<project_path>/docker/env_file.env`: This file contains environment variables that are used by the docker-compose files. You can add or remove variables as needed.
- `<project_path>/docker/settings_local.py`: This file is copied into the arches project when the container is started. If you need to set specific development environment settings, do it here. Note that if you change the settings_local.py file copied to the your arches project directory, it will be overwritten when the container is next stopped/started/restarted, so you should always change it in the `<project_path>/docker/settings_local.py` file.
   > ROADMAP - We'll look to provide a way to manage settings_local.py synchronisation in the future as part of the `manage up/down` commands.

## Contributing

Guidelines for contributing to the project are still being decided. Please check back later for more information.

The key principles are:

- It is designed to onboard new developers to the Arches project so the commands should be easy to understand and use.
- Keep the the functionality as simple as possible.
- Advanced functionality should not be a requirement for the majority of users.

While we work out the contribution guyideline, the following steps can be followed:

1. Fork the repository and create your branch from `main`.
1. Raise a ticket with details of the enhancement or bug being fixed.
1. Write or update tests as necessary.
1. Submit a pull request with a clear description of the changes.

## License

This project is licensed under the GNU AFFERO GENERAL PUBLIC LICENSE Version 3.
