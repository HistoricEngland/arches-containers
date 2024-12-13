import os, json
import arches_containers as ac

AC_DIRECTORY_NAME = ".arches_containers"
# INTERNAL FUCTIONS
def _get_ac_module_path():
    '''
    Returns the path to the arches-containers python module. Used to locate the template directory.
    '''
    return os.path.dirname(ac.__file__)

def _get_ac_context():
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

def _get_ac_directory_path():
    '''
    Returns the path of the .arches-containers directory.
    '''
    return os.path.join(_get_ac_context(), AC_DIRECTORY_NAME)

def _get_ac_project_path(project_name):
    '''
    Returns the path to the project directory.
    '''
    context = _get_ac_directory_path()
    project_path = os.path.join(context, project_name)

    if not os.path.exists(project_path) and not os.path.isdir(project_path):
        raise Exception(f"Project does not exist: {project_name}")
    return project_path

def _list_ac_projects():
    '''
    Returns a list of all projects in the .arches-containers directory.
    '''
    context =_get_ac_directory_path()
    return [name for name in os.listdir(context) if os.path.isdir(os.path.join(context, name))]

# PUBLIC CLASSES
class AcProjectConfig:
    '''
    Provides access to the configuration for a project.

    The configuration is stored in a JSON file in the project directory.

    It follows a dictionary-like interface, so you can access configuration values like this:
    
        ```
        config = AcProjectConfig("my_project")
        print(config["arches_version"])
        ```

    You can also set values like this:
    
            ```
            config["arches_version"] = "6.0.0"
            config.save()
            ```
    > TODO: It uses a dictionary as configurations could change between version templates. At some point we'll create versioned configuration classes using a factory pattern.
    '''
    def __init__(self, project_name):
        self.project_name = project_name
        
        config_path = os.path.join(_get_ac_project_path(project_name), "config.json")
        try:
            with open(config_path, "r") as config_file:
                self._config = json.load(config_file)
        except FileNotFoundError:
            raise Exception(f"Configuration file not found for {project_name}. Run 'arches-containers create' to create a new project.")

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self.config[key] = value

    def save(self):
        project_path = _get_ac_project_path(self.project_name)
        config_path = os.path.join(project_path, "config.json")
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)

    def get_project_path(self):
        return _get_ac_project_path(self.project_name)
    
    @staticmethod
    def generate_project_path(project_name):
        ac_directory = _get_ac_directory_path()
        project_path = os.path.join(ac_directory, project_name)
        if os.path.exists(project_path):
            raise Exception(f"Project already exists: {project_name}")
        return project_path


class AcSettings:
    def __init__(self):
        self.context = _get_ac_context()
        self.directory = _get_ac_directory_path()
        self.projects = _list_ac_projects()
        self.settings = self.load_settings()

    def load_settings(self):
        settings_path = os.path.join(self.directory, "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as settings_file:
                return json.load(settings_file)
        else:
            return {
                "default_project": None,
            }
    
    def save_settings(self):
        settings_path = os.path.join(self.directory, "settings.json")
        with open(settings_path, "w") as settings_file:
            json.dump(self.settings, settings_file, indent=4)

    def set_default_project(self, project_name):
        if project_name not in self.projects:
            raise Exception(f"Project does not exist: {project_name}")
        self.settings["default_project"] = project_name
        self.save_settings()

    def get_default_project(self) -> AcProjectConfig:
        if self.settings["default_project"] is None:
            try:
                self.set_default_project(self.projects[0])
            except IndexError:
                raise Exception("No projects found. Run 'arches-containers create' to create a new project.")
            self.save_settings()
        return AcProjectConfig(self.settings["default_project"])
    
    def _get_settings_path(self):
        '''
        Returns the path to the settings.json file.
        '''
        return os.path.join(self.context, "settings.json")
    
    def get_ac_module_path(self):
        '''
        Returns the path to the arches-containers python module. Used to locate the template directory.
        '''
        return _get_ac_module_path()
    
    def get_ac_context(self):
        '''
        Returns the path to the directory containing the .arches-containers directory.
        '''
        return self.context
    
