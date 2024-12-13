import os, json
import arches_containers as ac

def get_ac_module_path():
    '''
    Returns the path to the arches-containers module.
    '''
    return os.path.dirname(ac.__file__)

AC_DIRECTORY = ".arches_containers"

def get_ac_context():
    '''
    Returns the path to the .arches-containers directory.
    '''
    
    # traverse up the directory tree from the cwd to find the .arches-containers directory and if it does not exist, create it in the cwd
    cwd = os.getcwd()
    while cwd != "/":
        context = os.path.join(cwd, AC_DIRECTORY)
        if os.path.exists(context):
            return cwd
        cwd = os.path.dirname(cwd)

    # if you've got here then the .arches-containers directory does not exist in the cwd or any of its parent directories
    # so create it in the cwd
    context = os.path.join(os.getcwd(), AC_DIRECTORY)
    os.makedirs(context)
    return os.getcwd()

def get_ac_directory_path():
    '''
    Returns the path to the .arches-containers directory.
    '''
    return os.path.join(get_ac_context(), AC_DIRECTORY)

def get_ac_project_path(project_name):
    '''
    Returns the path to the project directory.
    '''
    context = get_ac_directory_path()
    project_path = os.path.join(context, project_name)

    if not os.path.exists(project_path) and not os.path.isdir(project_path):
        raise Exception(f"Project does not exist: {project_name}")
    return project_path

def get_ac_config(project_name):
    '''
    Returns the configuration for the current project.
    '''
    config_path = os.path.join(get_ac_project_path(project_name), "config.json")
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        raise Exception(f"Configuration file not found for {project_name}")
    
    return config

def list_ac_projects():
    '''
    Returns a list of all projects in the .arches-containers directory.
    '''
    context = get_ac_directory_path()
    return [name for name in os.listdir(context) if os.path.isdir(os.path.join(context, name))]

class AcConfig:
    def __init__(self, project_name):
        self.project_name = project_name
        self.config = get_ac_config(project_name)

    def __getitem__(self, key):
        return self.config[key]

    def __setitem__(self, key, value):
        self.config[key] = value

    def save(self):
        project_path = get_ac_project_path(self.project_name)
        config_path = os.path.join(project_path, "config.json")
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)