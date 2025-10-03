import platform
import re
import os, json, sys
import shutil

from slugify import slugify
import arches_containers
from enum import Enum
import datetime
from arches_containers.utils.logger import AcOutputManager
from arches_containers.utils.status import get_running_containers

AC_DIRECTORY_NAME = ".arches_containers"

# HELPER FUNCTIONS
def _get_ac_module_path():
    '''
    Returns the path to the arches-containers python module. Used to locate the template directory.
    '''
    return os.path.dirname(arches_containers.__file__)

def _adjust_platform_lines(target_path, uncomment: bool):
    """
    Adjusts platform lines in docker-compose files.
    If uncomment=True, uncomment '#platform: linux/arm64'
    If uncomment=False, comment 'platform: linux/arm64'
    """
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(".yml") or file.endswith(".yaml"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    content = f.read()
                if uncomment:
                    # Remove only the first '#' (and any following space) before 'platform: linux/arm64', preserving indentation
                    new_content = re.sub(r'^(\s*)#(\s*)(platform:\s*linux/arm64)', r'\1\3', content, flags=re.MULTILINE)
                else:
                    # Add a '#' before 'platform: linux/arm64' if not already commented, preserving indentation
                    new_content = re.sub(r'^(\s*)(platform:\s*linux/arm64)', r'\1#\2', content, flags=re.MULTILINE)
                if new_content != content:
                    with open(file_path, "w") as f:
                        f.write(new_content)

TEMPLATE_PATH = os.path.join(_get_ac_module_path(), "template")
REPLACE_TOKEN = "{{project}}"
REPLACE_TOKEN_URLSAFE = "{{project_urlsafe}}"


DEFAULT_AC_SETTINGS = {
    "active_project": "",
    "host": "localhost",
    "port": 8002,
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
            AcOutputManager.fail(f"Project configuration for '{project_name}' not found.")
            exit(1)

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
                
                # if any settigns are missing, add them
                settings = json.load(settings_file)
                missing_settings = False
                for key in DEFAULT_AC_SETTINGS:
                    if key not in settings:
                        settings[key] = DEFAULT_AC_SETTINGS[key]
                        missing_settings = True

                if missing_settings:
                    self.save_settings(settings)

                return settings
        else:
            return DEFAULT_AC_SETTINGS
    
    def save_settings(self, settings):
        with open(self._config_path, "w") as settings_file:
            json.dump(settings, settings_file, indent=4)

    def set_active_project(self, project_name):
        if project_name not in self._workspace.list_projects():
            AcOutputManager.fail(f"Project '{project_name}' does not exist.")
            exit(1)
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
                AcOutputManager.fail("No active project found. Provide a project name or run 'arches-containers create' to create a new project.")
                return None
        
        active_project = self._workspace.get_project(self.settings["active_project"])
        if active_project is None:
            AcOutputManager.fail("No active project found. Provide a project name or run 'arches-containers create' to create a new project.")
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
        
        If it doesn't find one having traversed to root, it'll create one in the current working directory.
        '''
        cwd = os.getcwd()
        while True:
            context = os.path.join(cwd, AC_DIRECTORY_NAME)
            if os.path.exists(context):
                return cwd
            parent_dir = os.path.dirname(cwd)
            if parent_dir == cwd or parent_dir == '/' or parent_dir.endswith(':\\'):
                cwd = os.getcwd()
                break
            cwd = parent_dir

        context = os.path.join(os.getcwd(), AC_DIRECTORY_NAME)
        os.makedirs(context)
        AcOutputManager.write(f"> Created .arches-containers directory at {context}")
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
            AcOutputManager.fail(f"Arches version {version} not supported.")
            exit(1)
        
        target_path = os.path.join(self._get_ac_directory_path(), project_name)
        if os.path.exists(target_path):
            AcOutputManager.fail(f"Project {project_name} already exists.")
            exit(1)

        shutil.copytree(template_folder, target_path)
        self._replace_projectname_placeholder(project_name, target_path)

        # Adjust platform lines for arm64
        if platform.machine() == "arm64" or platform.machine() == "aarch64":
            _adjust_platform_lines(target_path, uncomment=True)
        
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
        try:
            return AcProject(project_name, self._get_ac_directory_path())
        except FileNotFoundError:
            AcOutputManager.fail(f"Project '{project_name}' not found.")
            exit(1)

    def create_project(self, project_name, args):
        '''
        Creates a new project directory.
        '''

        if project_name is None or project_name == "":
            AcOutputManager.fail("Project name is required.")

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
        
        AcOutputManager.success(f"Project '{project_name}' created successfully.")
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

        AcOutputManager.success(f"Project {project_name} deleted.")

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

    def export_project(self, project_name, repo_path):
        '''
        Exports a project from the .arches-containers folder to the root of a given repo folder.
        '''
        EXPORT_AC_FOLDER = f".ac_{project_name}"

        project = self.get_project(project_name)
        if project is None:
            raise Exception(f"Project {project_name} not found.")
        
        project_path = project.get_project_path()
        ac_repo_path = os.path.join(repo_path, EXPORT_AC_FOLDER)
        
        if os.path.exists(ac_repo_path):
            AcOutputManager.stop_spinner()
            confirm = input(f"The directory {ac_repo_path} already exists. Proceed? (y/n): ")
            AcOutputManager.start_spinner()
            if confirm.lower() != 'y':
                AcOutputManager.write("> Export cancelled.")
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            new_ac_repo_path = f"{ac_repo_path}_{timestamp}"
            os.rename(ac_repo_path, new_ac_repo_path)
            AcOutputManager.write(f"> Existing {EXPORT_AC_FOLDER} directory renamed to {new_ac_repo_path}")
        
        if not os.path.exists(ac_repo_path):
            os.makedirs(ac_repo_path)
        
        for item in os.listdir(project_path):
            s = os.path.join(project_path, item)
            d = os.path.join(ac_repo_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        # Modify Docker YAML files
        for root, dirs, files in os.walk(ac_repo_path):
            for file in files:
                if file.endswith(".yml") or file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r+") as f:
                        content = f.read()
                        content = content.replace(f"/.arches_containers/{project_name}", f"/{project_name}/{EXPORT_AC_FOLDER}")
                        f.seek(0)
                        f.write(content)
                        f.truncate()
                        
        # Always comment out platform lines on export
        _adjust_platform_lines(ac_repo_path, uncomment=False)
        AcOutputManager.success(f"Project {project_name} exported to {ac_repo_path}.")

    def import_project(self, project_name, repo_path):
        '''
        Imports a project from the root of a given repo folder to the .arches-containers folder.
        '''
        IMPORT_AC_FOLDER = f".ac_{project_name}"
        ac_repo_path = os.path.join(repo_path, IMPORT_AC_FOLDER)
        if not os.path.exists(ac_repo_path):
            AcOutputManager.fail(f"Failed to import project. The directory {ac_repo_path} does not exist. Ensure the path is correct or use the --repo_path option if the repo directory name does not match the project name. The .ac folder must be called {IMPORT_AC_FOLDER}.")
            exit(1)
        
        project_path = os.path.join(self._get_ac_directory_path(), project_name)
        
        if os.path.exists(project_path):
            AcOutputManager.stop_spinner()
            confirm = input(f"The project {project_name} already exists. Proceed? (y/n): ")
            AcOutputManager.start_spinner()
            if confirm.lower() != 'y':
                AcOutputManager.success("Import cancelled.")
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            new_project_path = f"{project_path}_{timestamp}"
            os.rename(project_path, new_project_path)
            AcOutputManager.success(f"Existing project directory renamed to {new_project_path}")
        
        shutil.copytree(ac_repo_path, project_path, dirs_exist_ok=True)
        
        # Modify Docker YAML files
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith(".yml") or file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r+") as f:
                        content = f.read()
                        content = content.replace(f"/{project_name}/{IMPORT_AC_FOLDER}", f"/.arches_containers/{project_name}")
                        f.seek(0)
                        f.write(content)
                        f.truncate()
        # Adjust platform lines for arm64
        if platform.machine() == "arm64" or platform.machine() == "aarch64":
            _adjust_platform_lines(project_path, uncomment=True)
        AcOutputManager.success(f"Project {project_name} imported from {ac_repo_path}.")

    
