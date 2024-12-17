import os
import subprocess
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.create_launch_config import create_launch_config

DOCKER_COMPOSE_INIT_FILE = "docker-compose-init.yml"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
DOCKER_COMPOSE_DEPENDENCIES_FILE = "docker-compose-dependencies.yml"

def compose_project(project_name, action="up", build=False):
    project = AcWorkspace().get_project(project_name)
    project_path = project.get_project_path()    
    compose_files = [DOCKER_COMPOSE_DEPENDENCIES_FILE, DOCKER_COMPOSE_FILE]
    if action == "down":
        compose_files.reverse()
    
    for compose_file in compose_files:
        compose_file_path = os.path.join(project_path, compose_file)
        if not os.path.exists(compose_file_path):
            print(f"{compose_file} not found in {project_path}.")
            exit(1)
    
    for compose_file in compose_files:
        compose_file_path = os.path.join(project_path, compose_file)
        command = ["docker", "compose", "-f", compose_file_path, action]
        if action == "up":
            command.append("-d")
            if build:
                command.append("--build")
        
        print(f"Running: {' '.join(command)}")
        os.chdir(project_path)
        subprocess.run(command)

def initialize_project(project_name):
    # first check if the project is already initialized
    # seel if there is a folder in the workspace path with the project name
    WORKSPACE = AcWorkspace()
    config = WORKSPACE.get_project(project_name)
    if os.path.exists(config.get_project_path()):
        print(f"Project {project_name} is already initialized.")
        exit(1)

    project_path = config.get_project_path()
    
    compose_file_path = os.path.join(project_path, DOCKER_COMPOSE_INIT_FILE)
    if not os.path.exists(compose_file_path):
        print(f"{DOCKER_COMPOSE_INIT_FILE} not found in {project_path}.")
        exit(1)
    
    os.chdir(project_path)
    command = ["docker", "compose", "-f", compose_file_path, "up", "--exit-code-from", config["project_name_url_safe"]]
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode == 0:
        result = subprocess.run(["docker", "compose", "-f", compose_file_path, "down"])
    else:
        print("Initialization failed.")

    if result.returncode == 0:
        create_launch_config()
        print("Initialization successful.")

def main(project_name=None, action="up", build=False):
    WORKSPACE = AcWorkspace()
    if project_name is None:
        project_name = WORKSPACE.get_default_project_name()

    CONFIG = WORKSPACE.get_project(project_name)
    organization = CONFIG["arches_repo_organization"]

    if action == "init":
        # install arches if not already installed
        arches_repo_helper.clone_and_checkout_repo(project_name, organization)
        initialize_project(project_name)
        pass
    else:
        compose_project(project_name, action, build)