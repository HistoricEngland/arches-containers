import inspect
import json
import os
import subprocess
import argparse
from arches_containers.utils.ac_context import get_ac_context, get_ac_project_path, get_ac_config


def get_project_version(project_name):
    config = get_ac_config(project_name)
    return config["arches_version"]

def clone_and_checkout_repo(version, organization):
    repo_url = f"https://github.com/{organization}/arches.git"
    clone_dir = f"{get_ac_context()}/arches"
    
    if not os.path.exists(clone_dir):
        subprocess.run(["git", "clone", repo_url, clone_dir])
    
    os.chdir(clone_dir)
    subprocess.run(["git", "checkout", f"dev/{version}.x"])

def main(project_name=None, organization="archesproject"):
    if project_name is None:
        parser = argparse.ArgumentParser(description="Clone and checkout the correct development branch of the arches repo.")
        parser.add_argument("-p", "--project_name", required=True, help="The name of the project")
        parser.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the repo (default: archesproject)")
        args = parser.parse_args()
        project_name = args.project_name
        organization = args.organization
    
    version = get_project_version(project_name)
    clone_and_checkout_repo(version, organization)

if __name__ == "__main__":
    main()
