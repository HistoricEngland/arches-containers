import os, sys
import subprocess
from time import sleep
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.utils.logger import AcOutputManager
from arches_containers.utils.status import get_running_containers

DOCKER_COMPOSE_INIT_FILE = "docker-compose-init.yml"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
DOCKER_COMPOSE_DEPENDENCIES_FILE = "docker-compose-dependencies.yml"


def test_project_service_available_with_status_200(project_name) -> bool:
    '''
    Test if the project service is available.
    '''
    ac_settings = AcWorkspace().get_settings().settings
    host = ac_settings["host"]
    port = ac_settings["port"]
    url = f"http://{host}:{port}/"
    result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}\n", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0 and result.stdout != "200":
        return False
    else:
        return True

def compose_project(project_name, action="up", build=False, verbose=False, container_type="both"):
    '''
    Compose the project using docker-compose.yml and docker-compose-dependencies.yml files.
    container_type can be 'both', 'app', or 'dep' to control which containers are affected.
    '''
    container_desc = {
        "both": "project",
        "app": "application",
        "dep": "dependency"
    }
    AcOutputManager.text(f"{'starting' if action == 'up' else 'stopping'} {container_desc[container_type]} containers")
    project = AcWorkspace().get_project(project_name)
    project_path = project.get_project_path()    
    
    # Select compose files based on container_type
    if container_type == "app":
        compose_files = [DOCKER_COMPOSE_FILE]
    elif container_type == "dep":
        compose_files = [DOCKER_COMPOSE_DEPENDENCIES_FILE]
    else:  # container_type == "both"
        compose_files = [DOCKER_COMPOSE_DEPENDENCIES_FILE, DOCKER_COMPOSE_FILE]
        if action == "down":
            compose_files.reverse()
    
    for compose_file in compose_files:
        compose_file_path = os.path.join(project_path, compose_file)
        if not os.path.exists(compose_file_path):
            AcOutputManager.failed_step(f"{compose_file} not found in {project_path}.")
    
    for compose_file in compose_files:
        if compose_file == DOCKER_COMPOSE_FILE and action == "up":
            subprocess.run(["sleep", "15"])

        compose_file_path = os.path.join(project_path, compose_file)
        command = ["docker", "compose", "-f", compose_file_path, action]
        if action == "up":
            command.append("-d")
            if build:
                command.append("--build")
        
        os.chdir(project_path)
        if verbose:
            result = subprocess.run(command)
        else:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if result.returncode != 0:
            AcOutputManager.fail(f"failed to run {compose_file}.")
        else:
            AcOutputManager.complete_step(f"{'dependency' if compose_file == DOCKER_COMPOSE_DEPENDENCIES_FILE else 'project'} containers {'started' if action == 'up' else 'stopped'}.")

    AcOutputManager.complete_step(f"{container_desc[container_type]} containers for project {project_name} {'started' if action == 'up' else 'stopped'}.")
    if action == "up" and container_type in ["both", "app"]:
        AcOutputManager.text("awaiting project service availability")
        AcOutputManager.write("... ℹ️ depending on your application configuration this may take a while.")
        AcOutputManager.write("...    check container logs for detailed information.")
        while True:
            sleep(5)
            if test_project_service_available_with_status_200(project_name):
                AcOutputManager.complete_step("awaiting project service availability")
                AcOutputManager.complete_step("project service available.")
                break


def initialize_project(project_name, verbose=False):
    '''
    Initialize the project using the docker-compose-init.yml file.
    '''
    ac_workspace = AcWorkspace()
    if os.path.exists(os.path.join(ac_workspace.path, project_name)):
        AcOutputManager.complete_step(f"project {project_name} already initialized.")

    AcOutputManager.text("initializing project - building the development image if not available.")
    config = ac_workspace.get_project(project_name)
    project_path = config.get_project_path()
    
    compose_file_path = os.path.join(project_path, DOCKER_COMPOSE_INIT_FILE)
    if not os.path.exists(compose_file_path):
        AcOutputManager.fail(f"{DOCKER_COMPOSE_INIT_FILE} not found in {project_path}.")

    os.chdir(project_path)
    command = ["docker", "compose", "-f", compose_file_path, "up", "--exit-code-from", config["project_name_url_safe"]]
    if verbose:
        result = subprocess.run(command)
        if result.returncode == 0:
            result = subprocess.run(["docker", "compose", "-f", compose_file_path, "down"])
        else:
            AcOutputManager.fail("failed to build the development image during initialisation.")
    else:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            result = subprocess.run(["docker", "compose", "-f", compose_file_path, "down"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            AcOutputManager.fail("failed to build the development image during initialisation.")

    # now that the docker compose process has created the project directory, we can run the pre-commit install in the directory. make sure the virtualenv is activated.
    os.chdir(project_path)
    
    # Check if the directory is a git repository before attempting to install pre-commit
    git_check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if git_check.returncode == 0:
        # Directory is a git repository, install pre-commit
        result = subprocess.run([sys.executable, "-m", "pre_commit", "install"])
        if result.returncode != 0:
            AcOutputManager.fail("failed to run pre-commit install.")
        else:
            AcOutputManager.complete_step("pre-commit install complete.")
    else:
        AcOutputManager.write("... ℹ️ skipping pre-commit install - not a git repository.")

    AcOutputManager.complete_step("initialization complete.")

def status():
        ac_settings = AcWorkspace().get_settings()
        active_project = ac_settings.get_active_project()
        if not active_project:
            AcOutputManager.fail("No active project set. Run 'arches-containers activate' to set an active project.")
        
        project_name = active_project.project_name
        project_name_urlsafe = active_project["project_name_url_safe"]
        get_running_containers(project_name, project_name_urlsafe)

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