import os
import subprocess
from arches_containers.utils.workspace import AcWorkspace, AcProjectSettings


def _get_repo_info(project_name):
    ac_workspace = AcWorkspace()
    ac_project = ac_workspace.get_project(project_name)
    branch = ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value]
    repo_url = f"https://github.com/{ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value]}/arches.git"
    clone_dir = f"{ac_workspace.path}/arches"
    return (ac_project, repo_url, clone_dir, branch)

def clone_and_checkout_repo(project_name):
    ac_project, repo_url, clone_dir, branch = _get_repo_info(project_name)
    
    if not os.path.exists(clone_dir):
        results = subprocess.run(["git", "clone", repo_url, clone_dir])
        if results.returncode != 0:
            print(f"Failed to clone repo from {repo_url}")
            exit(1)

    change_arches_branch(project_name)

def change_arches_branch(project_name):
    ac_project, repo_url, clone_dir, branch = _get_repo_info(project_name)
    os.chdir(clone_dir)
    result = subprocess.run(["git", "checkout", branch])
    if result.returncode != 0:
        print(f"Failed to checkout branch {branch}")
        exit(1)
    
    print(f"Changed branch to {branch}")