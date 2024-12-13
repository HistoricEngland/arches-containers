import sys, os, inspect
import argparse
import shutil
from slugify import slugify
from arches_containers.utils.ac_context import get_ac_context, get_ac_module_path

# copy directory and rename to first arg
template_path = os.path.join(get_ac_module_path(), "template")
context = get_ac_context()
replace_token = "{{project}}"
replace_token_urlsafe = "{{project_urlsafe}}"

def get_target_path(project_name):
    return os.path.join(context, project_name)

def get_template_folder(version):
    version = f"_{version}_"
    root_dir = template_path
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            if version in dirname:
                return os.path.join(dirpath, dirname)
    return None

def get_urlsafe_project_name(project_name):
    return slugify(text=project_name, separator="")

def create_proj_directory(project_name, version):
    target_path = get_target_path(project_name)
    template_folder = get_template_folder(version)
    
    if template_folder is None:
        raise Exception("ERROR: version not correct or not yet supported.")
    
    if os.path.exists(target_path):
        raise Exception(f"ERROR: project path exists: {target_path}")
    
    shutil.copytree(template_folder, target_path)
    replace_projectname_placeholder(project_name)
    return target_path
    
def replace_projectname_placeholder(project_name):
    for dname, dirs, files in os.walk(get_target_path(project_name)):
        for fname in files:
            fpath = os.path.join(dname, fname)
            with open(fpath) as f:
                s = f.read()
            s = s.replace(replace_token, project_name)
            s = s.replace(replace_token_urlsafe, get_urlsafe_project_name(project_name))
            with open(fpath, "w") as f:
                f.write(s)

def handle_create_container_project(args):
    project_name = slugify(text=args.project_name, separator="_")
    version = args.version.lower()
    print(f"Creating container project {project_name}")
    print(f"... path: {create_proj_directory(project_name, version)}")
    print(f"{'-' * 5} Completed {'-' * 5}")
    
def main():
    # supported args
    parser = argparse.ArgumentParser(prog="Arches Container Project Generator",
                                     description="Creates an arches container project that sets up all the required files and default values for running an Arches instance in Docker using docker-compose")

    # main requirement is the project name
    parser.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    args = parser.parse_args()

    handle_create_container_project(args)

if __name__ == "__main__":
    main()

