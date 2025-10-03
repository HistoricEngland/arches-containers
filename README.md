# Arches Containers

## Overview

Arches Containers is a developer CLI tool to create and manage containerized Arches development environments. See [Arches](https://github.com/archesproject/arches) project for information related to the framework.

It is not an official Arches Project tool, but a community project to help developers get started with Arches development.

It provides commands to create and manage arches-container projects, which contain the necessary configuration files to run Arches in a containerized environment for development, complete with required minimum dependencies and services.

> ⚠️ **It is not yet configured to build an image to be deployed to a hosted environment. The ability to create a basic deployable image is in the Roadmap.**

These arches-container projects can be shared with others or stored in a version control system. They can be exported to a repository folder and imported back into the workspace.

It can also be used to generate VSCode debug configurations to allow debugging code inside the containers.

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

## Usage

Use the `arches-containers` or shorthand `act` command to manage arches-container projects.

The following examples use the `act` command. Replace `act` with `arches-containers` if you prefer to use the full command.

> ⚠️ **arches-containers** will create a `.arches-containers` folder in the workspace directory to store project configurations. It will look for this up the file tree when running commands. Should there be another `.arches-containers` folder in the workspace directory, the CLI may not work as expected.

```sh
cd /path/to/workspace
act [OPTIONS] COMMAND [ARGS]...
```

> Note: The command is aliased as `act` for convenience (**a**rches-**c**ontainer **t**ool).

### Quick start

1. Create a new project:

    This creates the arches-container project configuration and sets it as the active project.

    ```sh
    act create -p my_project -v 7.5 --activate
    ```

1. Initialize the project:

    This sets up the Arches repo, builds the development container, and creates the Arches project directory.

    ```sh
    act init
    ```

1. Start the project:

    This starts the containers and the Arches development server.

    ```sh
    act up
    ```

1. Open a browser and navigate to `http://localhost:8002` once setup and webpack builds are complete.

### Create a Project

Steps to create a new container project.

```sh
cd /path/to/workspace
act create -p <project_name> -v <version> [-o <organization>] [--activate]
```

- `-p`, `--project_name`: The name of the project. This value will be slugified to lowercase with underscore separators.
- `-v`, `--version`, `--ver`: The Arches version the project will be using (major.minor format).
- `-o`, `--organization`: The GitHub organization of the Arches repo (default: archesproject).
- `--activate`: Activate the project after creation. If it is the first project then it will be activated by default.

### Managing Projects

The following commands are available for managing projects:

#### Start a Project

```sh
cd /path/to/workspace
act up [-p <project_name>] [-b] [-vb] [--app | --dep]
```

- `-p`, `--project_name`: The name of the project. If excluded, the active project will be used.
- `-b`, `--build`: Rebuild containers when composing up.
- `-vb`, `--verbose`: Print verbose output during the compose processes.
- `--app`: Only operate on application containers (docker-compose.yml). Mutually exclusive with --dep.
- `--dep`: Only operate on dependency containers (docker-compose-dependencies.yml). Mutually exclusive with --app.

#### Stop a Project

```sh
cd /path/to/workspace
act down [-p <project_name>] [-vb] [--app | --dep]
```

- `-p`, `--project_name`: The name of the project. If excluded, the active project will be used.
- `-vb`, `--verbose`: Print verbose output during the compose processes.
- `--app`: Only operate on application containers (docker-compose.yml). Mutually exclusive with --dep.
- `--dep`: Only operate on dependency containers (docker-compose-dependencies.yml). Mutually exclusive with --app.

#### Restart a Project

Restarts the project containers by stopping and then starting them. Useful for applying changes such as new dependencies or forcing a rebuild.

```sh
cd /path/to/workspace
act restart [-p <project_name>] [-b] [-vb] [--app | --dep]
```

- `-p`, `--project_name`: The name of the project. If excluded, the active project will be used.
- `-b`, `--build`: Rebuild containers when composing up (after stopping them).
- `-vb`, `--verbose`: Print verbose output during the compose processes.
- `--app`: Only operate on application containers (docker-compose.yml). Mutually exclusive with --dep.
- `--dep`: Only operate on dependency containers (docker-compose-dependencies.yml). Mutually exclusive with --app.

**Examples:**

Restart and force rebuild:

```sh
act restart -b
```

Restart with verbose output:

```sh
act restart -b -vb
```

Restart only application containers:

```sh
act restart --app
```

Restart only dependency containers with rebuild:

```sh
act restart --dep -b
```

#### Initialize a Project

```sh
cd /path/to/workspace
act init [-p <project_name>] [-vb]
```

- `-p`, `--project_name`: The name of the project. If excluded, the active project will be used.
- `-vb`, `--verbose`: Print verbose output during the compose processes.

#### Activate a Project

```sh
cd /path/to/workspace
act activate -p <project_name> [-vb]
```

- `-p`, `--project_name`: The name of the project to activate.
- `-vb`, `--verbose`: Print verbose output during the compose processes.

### List Projects

Steps to list all container projects.

```sh
cd /path/to/workspace
act list
```

### Delete a Project

Steps to delete an existing container project.

```sh
cd /path/to/workspace
act delete -p <project_name>
```

- `-p`, `--project_name`: The name of the project to delete.

### Generate Debug Config

Steps to generate a VSCode launch.json configuration for the workspace.

```sh
cd /path/to/workspace
act generate-debug-config
```

### Export a Project

The user can export an arches-container project to a repository folder. This is useful when the user wants to share the project with others or store it in a version control system. The export command will create a folder called `.ac` in the repository folder and copy the necessary files to it.

The docker compose files in the exported arches-container project will need to be run manually as the command only access those in the `.arches-containers` folder.

```sh
cd /path/to/workspace
act export [-p <project_name>] [-r <repo_path>]
```

- `-p`, `--project_name`: The name of the project to export. Default is the active project.
- `-r`, `--repo_path`: The path to the repository folder. Default is `<workspace directory path>/<project_name>`.

### Import a Project

The user can import an arches-container project from a repository folder. This is useful when the user wants to use a project that has been shared with them or stored in a version control system.

```sh
act import -p <project_name> [-r <repo_path>]
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
act import -p project1
```

To import `project2`:

```sh
cd /path/to/workspace
act import -p project2 -r ./a_different_repo
```

### Check Container Status

Steps to check container status of the active project.

```sh
cd /path/to/workspace
act status
```

### Quickly open the application in a browser

Steps to open the application in a browser.

```sh
cd /path/to/workspace
act view
```

## Configuration of the Project

The project is stored in a directory called `<workspace_path>/.arches-containers/<project_name>` (the **project path**)and is compromised of a config file and a variety of files used with docker compose to stand up and environment.

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

- `<project path>/docker/env_file.env`: This file contains environment variables that are used by the docker-compose files. You can add or remove variables as needed.
- `<project path>/docker/settings_local.py`: This file is copied into the arches project when the container is started. If you need to set specific development environment settings, do it here. Note that if you change the settings_local.py file copied to the your arches project directory, it will be overwritten when the container is next stopped/started/restarted, so you should always change it in the `<project path>/docker/settings_local.py` file.

   > ROADMAP - We'll look to provide a way to manage settings_local.py synchronisation in the future as part of the `up` and `down` commands.

## Testing

The project uses [pytest](https://docs.pytest.org/en/latest/) for testing. To run the tests, use the following command:

```sh
cd /path/to/arches-containers
pytest
```

## Publishing

Publishing to PyPI and TestPyPI is handled by GitHub Actions triggered on a release (to PyPI) or a merge into the `testpypi` branch (to TestPyPI).

### Version Numbering

Ensure the version number is updated in both pyproject.toml and the `arches_containers/__init__.py` file before triggering either action:

- **For PyPI releases** (triggered by GitHub release):
  - Final release: `1.2.0`
  - Release candidate: `1.2.0rc1`

- **For TestPyPI releases** (triggered by merge to `testpypi` branch):
  - Development release: `1.2.0.dev1`
  - Alpha release: `1.2.0a1`
  - Beta release: `1.2.0b1`

### Development Status Classifier

Also update the Development Status classifier in pyproject.toml to match your release type:

- **For PyPI releases**:
  
  ```text
  "Development Status :: 5 - Production/Stable"  # For final releases
  "Development Status :: 4 - Beta"               # For release candidates
  ```

- **For TestPyPI releases**:
  
  ```text
  "Development Status :: 3 - Alpha"              # For alpha/development releases
  "Development Status :: 4 - Beta"               # For beta releases
  ```

This ensures that both the version number and the development status accurately reflect the maturity of your release.

## Contributing

Guidelines for contributing to the project are still being decided. Please check back later for more information.

The key principles are:

- It is designed to onboard new developers to the Arches project so the commands should be easy to understand and use.
- Keep the the functionality as simple as possible.
- Advanced functionality should not be a requirement for the majority of users.

While we work out the contribution guyideline, the following steps can be followed:

1. Fork the repository and create your branch from `main`.
1. Raise a ticket with details of the enhancement or bug being fixed.
1. Write or update tests as necessary. Please ensure that all tests pass before submitting a pull request.
1. Submit a pull request with a clear description of the changes.

## License

This project is licensed under the GNU AFFERO GENERAL PUBLIC LICENSE Version 3.
