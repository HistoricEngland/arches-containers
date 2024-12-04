import json
import os
import subprocess
import argparse

def get_project_version(project_name):
    config_path = f"project/{project_name}/config.json"
    if not os.path.exists(config_path):
        print("Version not found. Only projects for version 8.0 and above support this command.")
        exit(1)
    with open(config_path, "r") as config_file:
        config = json.load(config_file)
    return config["arches_version"]

def clone_and_checkout_repo(version, organization):
    repo_url = f"https://github.com/{organization}/arches.git"
    clone_dir = "arches"
    
    if not os.path.exists(clone_dir):
        subprocess.run(["git", "clone", repo_url, clone_dir])
    
    os.chdir(clone_dir)
    subprocess.run(["git", "checkout", version])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clone and checkout the correct development branch of the arches repo.")
    parser.add_argument("-p", "--project_name", required=True, help="The name of the project")
    parser.add_argument("-o","--organization", default="archesproject", help="The GitHub organization of the repo (default: archesproject)")
    args = parser.parse_args()
    
    version = get_project_version(args.project_name)
    clone_and_checkout_repo(version, args.organization)
