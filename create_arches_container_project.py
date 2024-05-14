import sys, os, inspect
import argparse
import shutil
import re
from slugify import slugify

# copy directory and rename to first arg

context = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))
replace_token = "{{project}}"
replace_token_urlsafe = "{{project_urlsafe}}"

# Get the directory of the currently running script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory
parent_dir = os.path.dirname(script_dir)

# Get the parent folder name
parent_folder_name = os.path.basename(parent_dir)

def get_target_path(project_name):
    return os.path.join(context,"projects",project_name)

def get_template_folder(version):
    version = f"_{version}_"
    root_dir = os.path.join(context,"template")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            if version in dirname:
                return os.path.join(dirpath, dirname)
    return None

def get_urlsafe_project_name(project_name):
    return slugify(text=parent_folder_name + project_name, separator='')

def create_proj_directory(project_name, version, port_incrementor):
    target_path = get_target_path(project_name)
    template_folder = get_template_folder(version)
    
    if template_folder is None:
        raise Exception("ERROR: version not correct or not yet supported.")
    
    if os.path.exists(target_path):
        raise Exception(f"ERROR: project path exists: {target_path}")
    
    shutil.copytree(template_folder, target_path)
    replace_projectname_placeholder(project_name, port_incrementor)
    return target_path
    
def replace_projectname_placeholder(project_name, port_incrementor):
    for dname, dirs, files in os.walk(get_target_path(project_name)):
        for fname in files:
            fpath = os.path.join(dname, fname)
            with open(fpath) as f:
                s = f.read()
            s = s.replace(replace_token, project_name)
            s = s.replace(replace_token_urlsafe, get_urlsafe_project_name(project_name))
            s = increment_port_number(s, port_incrementor)
            with open(fpath, "w") as f:
                f.write(s)

def increment_port_number(s, port_incrementor):
    numbers = re.findall(r'{{(\d+)}}', s)
    for number in numbers:
            incremented_number = str(int(number) + int(port_incrementor))
            s = s.replace('{{' + number + '}}', incremented_number)
    return s

def handle_create_container_project():
    project_name = slugify(text=args.project_name, separator='_')
    version = args.version.lower()
    port_incrementor = args.port_incrementor if args.port_incrementor else 0
    print(f"Creating container project {project_name}")
    print(f"... path: {create_proj_directory(project_name, version, port_incrementor)}")
    print(f"{'-' * 5} Completed {'-' * 5}")
    
    


# supported args
parser = argparse.ArgumentParser(prog="Arches Container Project Generator",
                                 description="Creates an arches container project that sets up all the required files and default values for running an Arches instance in Docker using docker-compose")

# main requirement is the project name
parser.add_argument("-p","--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore seperators")
parser.add_argument("-v","--version", required=True, help="The arches version the project will be using (major.minor format)")
parser.add_argument("-pi", "--port_incrementor", required=False, help="Increments external facing port numbers by this value. Default is 0. Useful for running multiple projects on the same host.")
args = parser.parse_args()

if __name__ == '__main__':
    handle_create_container_project()
    
    