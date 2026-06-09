import os, sys
import subprocess
from time import sleep, time
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
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
        stdout=subprocess.PIPE,
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0 and result.stdout.strip() == "200"

def _image_build_needed(compose_file_path, project_path):
    '''
    Return True if any image referenced by the compose file does not exist locally
    (i.e. it will need to be built or pulled before containers can start).
    '''
    try:
        config_result = subprocess.run(
            ["docker", "compose", "-f", compose_file_path, "config", "--images"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            cwd=project_path
        )
        for image in config_result.stdout.splitlines():
            image = image.strip()
            if image:
                inspect = subprocess.run(
                    ["docker", "image", "inspect", image],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                if inspect.returncode != 0:
                    return True
    except Exception:
        pass
    return False


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
            sleep(15)

        compose_file_path = os.path.join(project_path, compose_file)

        if compose_file == DOCKER_COMPOSE_FILE and action == "up":
            if build or _image_build_needed(compose_file_path, project_path):
                AcOutputManager.write("... ℹ️ the development image needs to be built and may take a few minutes.")

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
    project_hash = config.get_project_hash()
    service_name = f"{config['project_name_url_safe']}-{project_hash}" if project_hash else config["project_name_url_safe"]
    command = ["docker", "compose", "-f", compose_file_path, "up", "--exit-code-from", service_name]
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


def _get_default_container_name(project_name):
    '''
    Returns the default container name for a project (the main application container).
    '''
    project = AcWorkspace().get_project(project_name)
    project_hash = project.get_project_hash()
    if project_hash:
        return f"{project['project_name_url_safe']}-{project_hash}"
    return project["project_name_url_safe"]


def _check_container_running(container_name):
    '''
    Returns True if the container is running, False if it exists but is stopped,
    or None if no container with that name exists.
    '''
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() == "true"


def _get_app_root(container_name):
    '''
    Returns the APP_ROOT environment variable from a running container, or None if not set.
    '''
    result = subprocess.run(
        ["docker", "exec", container_name, "printenv", "APP_ROOT"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip() or None
    return None


def shell_container(project_name, container=None, exec_cmd=None):
    '''
    Open an interactive shell or run a command in a project container.
    '''
    container_name = container if container else _get_default_container_name(project_name)
    running = _check_container_running(container_name)
    if running is None:
        AcOutputManager.fail(f"Container '{container_name}' not found. Is the project running? Try 'act up'.")
        return 1
    if not running:
        AcOutputManager.fail(f"Container '{container_name}' is not running. Start it with 'act up'.")
        return 1
    workdir_flags = []
    if container is None:
        app_root = _get_app_root(container_name)
        if app_root:
            workdir_flags = ["-w", app_root]
    if exec_cmd:
        command = ["docker", "exec"] + workdir_flags + [container_name, "sh", "-c", exec_cmd]
    else:
        AcOutputManager.write(f"... Opening shell in container '{container_name}'.")
        AcOutputManager.write("... ℹ️ Type 'exit' or press Ctrl+D to return to the terminal.")
        command = ["docker", "exec", "-it"] + workdir_flags + [container_name, "/bin/bash"]
    AcOutputManager.stop_spinner()
    result = subprocess.run(command)
    return result.returncode


def logs_container(project_name, container=None, follow=False):
    '''
    Show logs for a project container.
    '''
    container_name = container if container else _get_default_container_name(project_name)
    running = _check_container_running(container_name)
    if running is None:
        AcOutputManager.fail(f"Container '{container_name}' not found. Is the project running? Try 'act up'.")
        return 1
    if not running:
        if follow:
            AcOutputManager.fail(f"Container '{container_name}' is not running. Start it with 'act up'.")
            return 1
        else:
            AcOutputManager.warn(f"Container '{container_name}' is not running — showing last known logs.")
    command = ["docker", "logs", container_name]
    if follow:
        AcOutputManager.write(f"... Following logs for container '{container_name}'.")
        AcOutputManager.write("... ℹ️ Press Ctrl+C to stop and return to the terminal.")

        # pause for 3 seconds to give the user a chance to read the message before the logs start streaming
        sleep(3)
        command.append("-f")
    AcOutputManager.stop_spinner()
    try:
        result = subprocess.run(command)
    except KeyboardInterrupt:
        return 0
    return result.returncode

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