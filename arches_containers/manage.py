import os
import subprocess
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject
import arches_containers.utils.arches_repo_helper as arches_repo_helper

DOCKER_COMPOSE_INIT_FILE = "docker-compose-init.yml"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
DOCKER_COMPOSE_DEPENDENCIES_FILE = "docker-compose-dependencies.yml"

def compose_project(project_name, action="up", build=False, verbose=False):
    '''
    Compose the project using docker-compose.yml and docker-compose-dependencies.yml files.
    '''
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
        if compose_file == DOCKER_COMPOSE_FILE and action == "up":
            # wait 5 seconds for dependencies to start
            print("Waiting for dependencies to start...")
            subprocess.run(["sleep", "15"])

        compose_file_path = os.path.join(project_path, compose_file)
        command = ["docker", "compose", "-f", compose_file_path, action]
        if action == "up":
            command.append("-d")
            if build:
                command.append("--build")
        
        print(f"Running: {' '.join(command)}")
        os.chdir(project_path)
        if verbose:
            result = subprocess.run(command)
        else:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if result.returncode != 0:
            print(f"Failed to run {compose_file}.")
            exit(1)

def initialize_project(project_name, verbose=False):
    '''
    Initialize the project using the docker-compose-init.yml file.
    '''
    ac_workspace = AcWorkspace()
    if os.path.exists(os.path.join(ac_workspace.path, project_name)):
        print(f"Project {project_name} is already initialized.")
        exit(1)

    config = ac_workspace.get_project(project_name)
    project_path = config.get_project_path()
    
    compose_file_path = os.path.join(project_path, DOCKER_COMPOSE_INIT_FILE)
    if not os.path.exists(compose_file_path):
        print(f"{DOCKER_COMPOSE_INIT_FILE} not found in {project_path}.")
        exit(1)
    
    os.chdir(project_path)
    command = ["docker", "compose", "-f", compose_file_path, "up", "--exit-code-from", config["project_name_url_safe"]]
    print(f"Running: {' '.join(command)}")
    if verbose:
        result = subprocess.run(command)
        if result.returncode == 0:
            result = subprocess.run(["docker", "compose", "-f", compose_file_path, "down"])
        else:
            print("Initialization failed.")
    else:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            result = subprocess.run(["docker", "compose", "-f", compose_file_path, "down"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("Initialization failed.")

    print("Initialization complete.")

def main(project_name=None, action="up", build=False, verbose=False):
    ac_workspace = AcWorkspace()
    if project_name is None:
        project_name = ac_workspace.get_active_project_name()

    ac_project = ac_workspace.get_project(project_name)
    organization = ac_project["arches_repo_organization"]

    if action == "init":
        # install arches if not already installed
        arches_repo_helper.clone_and_checkout_repo(project_name, organization, verbose)
        initialize_project(project_name, verbose)
        pass
    else:
        arches_repo_helper.change_arches_branch(project_name)
        compose_project(project_name, action, build, verbose)