# arches-containers

Developer tool to easily setup an Arches development environment. It creates container "projects" that provide all the files needed, with essential settings preconfigured.

Just create a container project, start the dependencies compose, then start the project compose... and wait.

## Setup

Requires Docker for Desktop or comparible container runtime that supports compose.

**❗️ If you are using Apple Silicon devices, ensure that you have enabled Rosetta 2 support in Docker for Desktop advanced settings.**

Create a workspace folder to contain all repos and files.

Create your virtual environment `python -m venv env` or try using VSCode Dev Container.

To do the latter, install the Dev Containers extension so that development work can be done within the container and need no local installations. Use a Python base image (3.9 tested) with docker-in-docker feature enabled.

Clone this repo into the workspace folder and then install.

#### if using venv then activate, then in your /path/to/workspace
```sh
pip install . -e
```

## Usage

### 1. Create the container project
Use the create_arches_container_project script to generate all the docker files for an arches project. Call the script and provide the name of the project and the target arches version (major.minor format). v7.0+ supported.

#### in your /path/to/workspace/arches_containers
```sh
python3 create_arches_container_project.py -p myproject -v 7.4 
```
> WARNING: Known issues with separators in names so use continuous name for now e.g. mygreatproject.

This will create a directory of files under the "projects" directory with a slug of the project name given - an example would be `workspace/arches-continers/projects/mygreatproject`.


### 2. Starting up an arches environment

You'll need to clone down the arches repo to the root of your workspace and checkout the branch/tag that you want to use as a basis (should match the version stated when creating the container project).

#### in your /path/to/workspace
```sh
git clone https://github.com/archesproject/arches.git
```
```sh
cd arches
```
```sh
git checkout dev/7.4.x
```
Navigate you your container project directory.

If the arches project does not already exist at the root of the workspace then compose up the Compose up the `docker-compose-init.yml` first to generate the project. If you do want to use an existing arches project then ensure the repo has been cloned to the root of workspace first.

Next compose up the `docker-compose-dependencies.yml` to create and start all the service dependencies. Once the dependencies are up, compose up the `docker-compose.yml`.

If you are using this to create a new arches project, this may take a few minutes to complete building everything.

Note, the arches project created will not be initialised as a repo so that is left to you to do.

