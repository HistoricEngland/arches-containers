# Arches Containers

## Overview

Arches Containers is a tool to create and manage containerized Arches development environments.

It provides commands to create and manage arches-container projects, as well as generate VSCode debug configurations, and export arches-container projects to repositories for sharing. The tool is designed to be used with the [Arches](https://github.com/archesproject/arches) project.

## Installation

### From PyPI

1. Install the package:

    ```sh
    pip install arches-containers
    ```

### From Source

1. Clone the repository:

    ```sh
    git clone https://github.com/HistoricEngland/arches-containers.git
    cd arches-containers
    ```

2. Create a virtual environment and activate it:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the package:

    ```sh
    pip install .
    ```

## Usage

Use the `arches-containers` command to manage arches-container projects.

```sh
arches-containers [OPTIONS] COMMAND [ARGS]...
```

> Note: The command is aliased as `acon` for convenience.

### Create a Project

Steps to create a new container project.

```sh
arches-containers create -p <project_name> -v <version> [-o <organization>] [--activate]
```

- `-p`, `--project_name`: The name of the project. This value will be slugified to lowercase with underscore separators.
- `-v`, `--version`, `--ver`: The Arches version the project will be using (major.minor format).
- `-o`, `--organization`: The GitHub organization of the Arches repo (default: archesproject).
- `--activate`: Activate the project after creation. If it is the first project then it will be activated by default.

### Manage a Project

Steps to manage an existing container project.

```sh
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
arches-containers list
```

### Delete a Project

Steps to delete an existing container project.

```sh
arches-containers delete -p <project_name>
```

- `-p`, `--project_name`: The name of the project to delete.

### Generate Debug Config

Steps to generate a VSCode launch.json configuration for the workspace.

```sh
arches-containers generate-debug-config
```

### Export a Project

The user can export an arches-container project to a repository folder. This is useful when the user wants to share the project with others or store it in a version control system. The export command will create a folder called `.ac` in the repository folder and copy the necessary files to it.

The docker compose files in the exported arches-container project will need to be run manually as the command only access those in the `.arches-containers` folder.

> TODO: In future there will a command to import a project from a repository folder so it is available to the command line.

```sh
arches-containers export [-p <project_name>] [-r <repo_path>]
```

- `-p`, `--project_name`: The name of the project to export. Default is the active project.
- `-r`, `--repo_path`: The path to the repository folder. Default is `<workspace directory path>/<project_name>`.

## Contributing

Guidelines for contributing to the project are still being decided. Please check back later for more information.

In the meantime, the following steps can be followed:

1. Fork the repository and create your branch from `main`.
1. Raise a ticket with details of the enhancement or bug being fixed.
1. Write or update tests as necessary.
1. Submit a pull request with a clear description of the changes.

## License

This project is licensed under the GNU AFFERO GENERAL PUBLIC LICENSE Version 3.
