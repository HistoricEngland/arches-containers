import sys, os, inspect
import argparse
import shutil
from slugify import slugify

# copy directory and rename to first arg

context = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))
replace_token = "{{project}}"

def get_target_path(project_name):
    return os.path.join(context,"projects",project_name)

def create_proj_directory(project_name):
    target_path = get_target_path(project_name)
    if os.path.exists(target_path):
        raise Exception(f"Container project path exists: {target_path}")
    shutil.copytree(os.path.join(context,"template"), target_path)
    replace_projectname_placeholder(project_name)
    return target_path
    
def replace_projectname_placeholder(project_name):
    for dname, dirs, files in os.walk(get_target_path(project_name)):
        for fname in files:
            fpath = os.path.join(dname, fname)
            with open(fpath) as f:
                s = f.read()
            s = s.replace(replace_token, project_name)
            with open(fpath, "w") as f:
                f.write(s)

def handle_create_container_project():
    project_name = slugify(text=args.project_name, separator='_')
    print(f"Creating container project {project_name}")
    print(f"... path: {create_proj_directory(project_name)}")


def handle_create_arches_project():
    print("Create Arches application Project - Not implemented")
    pass

# supported args
parser = argparse.ArgumentParser(prog="Arches Container Project Generator",
                                 description="Creates an arches container project that sets up all the required files and default values for running an Arches instance in Docker using docker-compose")

# main requirement is the project name
parser.add_argument("project_name", help="The name of the project. This value will be slugified to lowercase with underscore seperators")

# should the arches application project be created? If you don't have an arches application project yet then use this flag to create one using the project_name.
parser.add_argument("-c","--create-arches-project", action='store_true', help="If you don't have an arches application project yet then use this flag to create one using the project_name. This will be created at the root of your workspace.")
args = parser.parse_args()

if __name__ == '__main__':
    #print(args.project_name)
    handle_create_container_project()
    print(f"{'_'*5} Completed {'_'*5}")