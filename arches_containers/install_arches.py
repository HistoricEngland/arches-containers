import os
import subprocess
from arches_containers.utils.ac_context import AcSettings

    
def clone_and_checkout_repo(version, organization):
    SETTINGS = AcSettings()
    repo_url = f"https://github.com/{organization}/arches.git"
    clone_dir = f"{SETTINGS.context}/arches"
    
    if not os.path.exists(clone_dir):
        subprocess.run(["git", "clone", repo_url, clone_dir])
    
    os.chdir(clone_dir)
    subprocess.run(["git", "checkout", f"dev/{version}.x"])

