import os
import subprocess
from urllib.parse import urlparse
from slugify import slugify
from arches_containers.utils.workspace import AcWorkspace, AcProjectAttributes
from arches_containers.utils.logger import AcOutputManager

def _get_repo_info(project_name):
    ac_workspace = AcWorkspace()
    ac_project = ac_workspace.get_project(project_name)
    branch = ac_project[AcProjectAttributes.PROJECT_ARCHES_REPO_BRANCH.value]
    repo_url = f"https://github.com/{ac_project[AcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value]}/arches.git"
    clone_dir = os.path.join(ac_workspace.path, "arches")
    return (ac_project, repo_url, clone_dir, branch)

def clone_and_checkout_repo(project_name, verbose=False):
    ac_project, repo_url, clone_dir, branch = _get_repo_info(project_name)
    
    if not os.path.exists(clone_dir):
        results = subprocess.run(
            ["git", "clone", repo_url, clone_dir],
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None
        )
        if results.returncode != 0:
            AcOutputManager.fail(f"failed to clone arches repo from {repo_url}")

    change_arches_branch(project_name, verbose)

def change_arches_branch(project_name, verbose=False):
    ac_project, repo_url, clone_dir, branch = _get_repo_info(project_name)

    # check the arches repo exists
    if not os.path.exists(clone_dir):
        clone_and_checkout_repo(project_name, verbose)
        return

    os.chdir(clone_dir)
    result = subprocess.run(
        ["git", "checkout", branch],
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None
    )
    if result.returncode != 0:
        AcOutputManager.fail(f"Failed to checkout arches branch {branch}")
    
    if verbose:
        AcOutputManager.write(f"Changed arches repo branch to {branch}")

    AcOutputManager.complete_step(f"Arches repo configured")


def derive_repo_directory_name(repo_url):
    parsed = urlparse(repo_url)
    basename = os.path.basename(parsed.path)
    if basename.endswith(".git"):
        basename = basename[:-4]
    name = slugify(text=basename, separator="-")
    if not name:
        raise ValueError(f"Cannot derive repository directory name from URL: {repo_url}")
    return name


def clone_repository(repo_url, clone_dir, verbose=False):
    if os.path.exists(clone_dir):
        return False

    result = subprocess.run(
        ["git", "clone", repo_url, clone_dir],
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
    )

    return result.returncode == 0