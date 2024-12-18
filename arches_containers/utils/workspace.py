import os, json
import shutil

from slugify import slugify
import arches_containers as ac
from enum import Enum

AC_DIRECTORY_NAME = ".arches_containers"

# HELPER FUNCTIONS
def _get_ac_module_path():
    '''
    Returns the path to the arches-containers python module. Used to locate the template directory.
    '''
    return os.path.dirname(ac.__file__)

TEMPLATE_PATH = os.path.join(_get_ac_module_path(), "template")
REPLACE_TOKEN = "{{project}}"
REPLACE_TOKEN_URLSAFE = "{{project_urlsafe}}"


DEFAULT_AC_SETTINGS = {
    "active_project": "",
}

# PUBLIC CLASSES

class AcProjectSettings(Enum):
    def __str__(self):
        return self.value
    PROJECT_NAME = "project_name"
    PROJECT_NAME_URLSAFE = "project_name_url_safe"
    PROJECT_ARCHES_VERSION = "arches_version"
    PROJECT_ARCHES_REPO_ORGANIZATION = "arches_repo_organization"
    PROJECT_ARCHES_REPO_BRANCH = "arches_repo_branch"

class AcProject:
    '''
    Provides access to the configuration for a project.

    The configuration is stored in a JSON file in the project directory (.arches-containers/<project_name>).
    '''
    def __init__(self, project_name, ac_directory_path):
        self._path = os.path.join(ac_directory_path, project_name) 
        self._config_path = os.path.join(self._path, "config.json")
        self.project_name = project_name
        try:
            with open(self._config_path, "r") as config_file:
                self._config = json.load(config_file)
        except FileNotFoundError:
            raise Exception(f"Configuration file not found for {project_name}. Run 'arches-containers create' to create a new project.")

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def save(self):
        with open(self._config_path, "w") as config_file:
            json.dump(self._config, config_file, indent=4)

    def get_project_path(self):
        return self._path

class AcSettings:
    '''
    Provides access to the settings for the workspace.

    The settings are stored in a JSON file in the .arches-containers directory.
    '''
    def __init__(self, workspace):
        self._workspace = workspace
        self._config_path = os.path.join(self._workspace._get_ac_directory_path(), "settings.json")

    @property
    def settings(self):
        return self._load_settings()

    def _load_settings(self):
        settings_path = os.path.join(self._workspace._get_ac_directory_path(), "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as settings_file:
                # if settings file is empty, return default settings
                if os.stat(settings_path).st_size == 0:
                    return DEFAULT_AC_SETTINGS
                
                return json.load(settings_file)
        else:
            return DEFAULT_AC_SETTINGS
    
    def save_settings(self, settings):
        with open(self._config_path, "w") as settings_file:
            json.dump(settings, settings_file, indent=4)

    def set_active_project(self, project_name):
        if project_name not in self._workspace.list_projects():
            raise Exception(f"Project does not exist: {project_name}")
        settings = self.settings
        settings["active_project"] = project_name
        self.save_settings(settings)

    def get_active_project(self) -> AcProject:
        '''
        Returns the active project configuration. 
        '''
        if self.settings["active_project"] == "":
            try:
                self.set_active_project(self._workspace.list_projects()[0])
            except IndexError:
                print("No active project found. Provide a project name or run 'arches-containers create' to create a new project.")
                return None
        
        active_project = self._workspace.get_project(self.settings["active_project"])
        if active_project is None:
            print("No active project found. Provide a project name or run 'arches-containers create' to create a new project.")
            return None
        
        return active_project
    
    def get_active_project_name(self):
        '''
        Returns the active project name.
        '''
        project = self.get_active_project()
        if project:
            return project.project_name
        return ""
    
    def _get_settings_path(self):
        '''
        Returns the path to the settings.json file.
        '''
        return os.path.join(str(self._workspace), "settings.json")
    
    def clear_active_project(self):
        settings = self.settings
        settings["active_project"] = ""
        self.save_settings(settings)

class AcWorkspace:
    def __init__(self):
        self._path = self._get_ac_workspace()

    def __str__(self):
        return self._path
    
    @property
    def path(self):
        return self._path

    # INTERNAL METHODS
    def _get_ac_workspace(self):
        '''
        Returns the path to the directory containing the .arches-containers directory.
        
        If it doesn't find one it'll create one in the current working directory.
        '''
        cwd = os.getcwd()
        while cwd != "/":
            context = os.path.join(cwd, AC_DIRECTORY_NAME)
            if os.path.exists(context):
                return cwd
            cwd = os.path.dirname(cwd)

        context = os.path.join(os.getcwd(), AC_DIRECTORY_NAME)
        os.makedirs(context)
        return os.getcwd()

    def _get_ac_directory_path(self):
        '''
        Returns the .arches-containers directory path.
        '''
        return os.path.join(self._path, AC_DIRECTORY_NAME)

    def _get_template_folder(self, version):
        version = f"_{version.lower()}_"
        root_dir = TEMPLATE_PATH
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for dirname in dirnames:
                if version in dirname:
                    return os.path.join(dirpath, dirname)
        return None

    def _get_urlsafe_project_name(self, project_name):
        return slugify(text=project_name, separator="")

    def _create_proj_directory(self, project_name, version):
        template_folder = self._get_template_folder(version)
        if template_folder is None:
            print(f"Arches version {version} not supported.")
            exit(1)
        
        target_path = os.path.join(self._get_ac_directory_path(), project_name)
        if os.path.exists(target_path):
            print(f"Project {project_name} already exists.")
            exit(1)

        shutil.copytree(template_folder, target_path)
        self._replace_projectname_placeholder(project_name, target_path)

        ac_settings = self.get_settings()
        
        if ac_settings.settings["active_project"] == "":
            ac_settings.set_active_project(project_name)
        return target_path
        
    def _replace_projectname_placeholder(self,project_name, target_path):
        for dname, dirs, files in os.walk(target_path):
            for fname in files:
                fpath = os.path.join(dname, fname)
                with open(fpath) as f:
                    s = f.read()
                s = s.replace(REPLACE_TOKEN, project_name)
                s = s.replace(REPLACE_TOKEN_URLSAFE, self._get_urlsafe_project_name(project_name))
                with open(fpath, "w") as f:
                    f.write(s)

    # PUBLIC METHODS
    def get_project(self, project_name) -> AcProject:
        '''
        Returns the path to the project directory.
        '''
        context = self._get_ac_directory_path()
        project_path = os.path.join(context, project_name)

        if not os.path.exists(project_path) and not os.path.isdir(project_path):
            print(f"Project {project_name} not found.")
            return None
        
        return AcProject(project_name, self._get_ac_directory_path())

    def create_project(self, project_name, args):
        '''
        Creates a new project directory.
        '''

        if project_name is None or project_name == "":
            print("Project name is required.")
            exit(1)

        # the project must be a valid slug where the only allowed characters are letters, numbers, and underscores. It must start with a letter. it must be lowercase.
        # create a function to slugify the project name
        project_name = slugify(text=project_name, separator="_")

        self._create_proj_directory(project_name, args.version)
        # update the project config if organization is provided in args
        project = self.get_project(project_name)
        if args.organization:
            project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
        if args.branch:
            project[AcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
        
        if args.organization or args.branch:
            project.save()
        
        print(f"Project {project_name} created.")
        return project
    
    def delete_project(self, project_name):
        '''
        Deletes a project directory.
        '''

        project = self.get_project(project_name)
        # remvove as the active project if it is the active project
        ac_settings = self.get_settings()
        if ac_settings.get_active_project_name() == project_name:
            ac_settings.clear_active_project()

        project_path = project.get_project_path()
        shutil.rmtree(project_path)

        print(f"Project {project_name} deleted.")

    def list_projects(self):
        '''
        Returns a list of all projects in the .arches-containers directory.
        '''
        context = self._get_ac_directory_path()
        return [name for name in os.listdir(context) if os.path.isdir(os.path.join(context, name))]

    def get_settings(self):
        '''
        Returns the AcSettings object.
        '''
        return AcSettings(self)