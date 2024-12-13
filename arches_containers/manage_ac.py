import os
import subprocess
import argparse
import inspect
from arches_containers.utils.ac_context import get_ac_context, get_ac_project_path, get_ac_config
import arches_containers.install_arches as install_arches_repo


def compose_project(project_name, action, build):
    project_path = get_ac_project_path(project_name)
    if not os.path.exists(project_path):
        print(f"Project {project_name} does not exist.")
        exit(1)
    
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

def initialize_project(project_name):
    project_path = get_ac_project_path(project_name)
    
    compose_file = "docker-compose-init.yml"
    compose_file_path = os.path.join(project_path, compose_file)
    if not os.path.exists(compose_file_path):
        print(f"{compose_file} not found in {project_path}.")
        exit(1)
    
    config = get_ac_config(project_name)
    os.chdir(get_ac_context())
    command = ["docker", "compose", "-f", compose_file_path, "up", "--exit-code-from", config["project_name_url_safe"]]
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode == 0:
        subprocess.run(["docker", "compose", "-f", compose_file_path, "down"])
    else:
        print("Initialization failed.")

def main():
    parser = argparse.ArgumentParser(description="Manage an Arches project using Docker Compose.")
    parser.add_argument("-p", "--project_name", required=True, help="The name of the project")
    parser.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the repo (default: archesproject)")
    parser.add_argument("action", choices=["up", "down", "init"], help="Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project")
    
    args = parser.parse_args()
    print(f"Parsed arguments: {args}") 

    if args.action == "init":
        # install arches if not already installed
        install_arches_repo.main(args.project_name, args.organization)

        initialize_project(args.project_name)
        pass
    else:
        compose_project(args.project_name, args.action, args.build)

if __name__ == "__main__":
    main()