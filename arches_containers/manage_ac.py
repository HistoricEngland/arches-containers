import os
import subprocess
from arches_containers.utils.ac_context import AcSettings, AcProjectConfig
import arches_containers.install_arches as install_arches_repo
from arches_containers.create_launch_config import create_launch_config



def compose_project(project_name=AcSettings().get_default_project().project_name, action="up", build=False):
    SETTINGS = AcSettings()
    project = AcProjectConfig(project_name)
    project_path = project.get_project_path()    
    compose_files = ["docker-compose-dependencies.yml", "docker-compose.yml"]
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

def initialize_project(project_name=AcSettings().get_default_project().project_name):
    # first check if the project is already initialized
    # seel if there is a folder in the ac_context path with the project name
    config = AcProjectConfig(project_name)
    SETTINGS = AcSettings()
    if os.path.exists(config.get_project_path()):
        print(f"Project {project_name} is already initialized.")
        exit(1)

    project_path = config.get_project_path()
    
    compose_file = "docker-compose-init.yml"
    compose_file_path = os.path.join(project_path, compose_file)
    if not os.path.exists(compose_file_path):
        print(f"{compose_file} not found in {project_path}.")
        exit(1)
    
    os.chdir(SETTINGS.context)
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

def list_projects():
    SETTINGS = AcSettings()
    default_project_name = SETTINGS.get_default_project().project_name
    projects = SETTINGS.projects
    if projects:
        print("Projects:")
        for project in projects:
            if project == default_project_name:
                print(f"\033[92m- {project} (default)\033[0m")
            else:
                print(f"- {project}")
    else:
        print("No projects found.")

def main(project_name=AcSettings().get_default_project().project_name, action="up", build=False):
    CONFIG = AcProjectConfig(project_name)
    organization = CONFIG["organization_name"]

    if action == "init":
        # install arches if not already installed
        install_arches_repo.clone_and_checkout_repo(project_name, organization)

        initialize_project(project_name)
        pass
    else:
        if action == "list":
            list_projects()
        else:
            compose_project(project_name, action, build)