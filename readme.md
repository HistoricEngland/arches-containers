# arches_containers - **under development**

## Setup

> REQUIRES Docker for Desktop

Install the Dev Containers extension so that development work can be done within the container and need no local installations.

```sh
/path/to/workspace/arches_containers $ pip install -r requirements.txt 
```

## Usage

Use the create_arches_container_project script to generate all the docker files for an arches project. Call the script and provide the name of the project arches version (major.minor format).

```sh
/path/to/workspace/arches_containers $ python3 create_arches_container_project.py -p my_project -v 7.4 
```

This will create a set of files in a directory with a slug of the prject name given under `arches_continers/projects`.


## Starting up an arches environment

You'll need to clone down the arches repo to the root of your workspace and checkout the branch/tag that you want to use as a basis.

```sh
/path/to/workspace $ git clone https://github.com/archesproject/arches.git
/path/to/workspace $ cd arches
/path/to/workspace/arches $ git checkout dev/7.4.x
```

Rather than using bat files, right click on the compose files and "Compose Up". Becuase the docker files are in their own projects, the volumes etc will be profixed with the project name.

Compose up the `docker-compose-dependencies.yml` first. Once the dependencies are up, compose up the `docker-compose.yml`.

If the project is not created, and in place at the root of the workspace then it'll be created. If you want to use and existing project then ensure the repo has been cloned down first.

