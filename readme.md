# arches_containers - **under development**

## Setup

> REQUIRES Docker for Desktop

Install the Dev Containers extension so that development work can be done within the container and need no local installations.



## Usage

Use the create_arches_container_project script to generate all the docker files for an arches project. Call the script and provide the name of the project as the only argument.

```sh
/path/to/workspace/arches_containers $ python3 create_arches_container_project my_project 
```

This will create a set of files in a directory with a slug of the prject name given under `arches_continers/projects`.