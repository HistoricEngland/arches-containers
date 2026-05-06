import platform
import re
import os, json, sys
import shutil
import hashlib
import secrets

from slugify import slugify
import arches_containers
from enum import Enum
import datetime
from arches_containers.utils.logger import AcOutputManager
from arches_containers.utils.status import has_running_project_containers

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
REPLACE_TOKEN_REPO = "{{project_repo_directory}}"
REPLACE_TOKEN_HASH = "{{project_hash}}"


def _version_supports_project_hash(arches_version: str) -> bool:
    """Return True only for Arches versions that support project_hash tokens (>= 7.6)."""
    try:
        parts = arches_version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, AttributeError, IndexError):
        return False
    return (major, minor) >= (7, 6)


def _is_version_supported(arches_version: str) -> bool:
    """Return True for Arches versions that are actively maintained (>= 7.6)."""
    return _version_supports_project_hash(arches_version)


def _generate_project_hash(project_path: str) -> str:
    # SHA1 is used here solely for generating a short deterministic identifier,
    # not for any security or cryptographic purpose.
    return hashlib.sha1(project_path.encode()).hexdigest()[:5]


def _generate_new_project_hash(current_hash: str = "") -> str:
    while True:
        generated_hash = secrets.token_hex(3)[:5]
        if generated_hash != current_hash:
            return generated_hash


def _normalize_and_validate_project_hash(project_hash: str) -> str:
    normalized_hash = (project_hash or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{5}", normalized_hash):
        raise ValueError("Hash must be a 5-character lowercase hexadecimal value (for example: a1b2c).")
    return normalized_hash


DEFAULT_AC_SETTINGS = {
    "active_project": "",
    "host": "localhost",
    "port": 8002,
}

# PUBLIC CLASSES

class AcProjectAttributes(Enum):
    def __str__(self):
        return self.value
    PROJECT_NAME = "project_name"
    PROJECT_NAME_URLSAFE = "project_name_url_safe"
    PROJECT_REPO_DIRECTORY = "project_repo_directory"
    PROJECT_HASH = "project_hash"
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

    def supports_project_hash(self) -> bool:
        arches_version = self._config.get(AcProjectAttributes.PROJECT_ARCHES_VERSION.value, "")
        return _version_supports_project_hash(arches_version)

    def get_project_hash(self) -> str:
        if not self.supports_project_hash():
            return ""
        return self._config.get(AcProjectAttributes.PROJECT_HASH.value, "")

    def is_initialised(self) -> bool:
        ac_workspace = AcWorkspace()
        repo_dir_name = self._config.get(
            AcProjectAttributes.PROJECT_REPO_DIRECTORY.value,
            self.project_name,
        )
        repo_dir = os.path.join(ac_workspace.path, repo_dir_name)
        return os.path.exists(repo_dir)

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
    
    def get_active_project_repo_name(self):
        ''' Returns the active project directory. '''
        project = self.get_active_project()
        if project:
            return project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] 
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
        return slugify(text=project_name, separator="-")

    def _create_proj_directory(self, project_name, version, repo_name=None):
        template_folder = self._get_template_folder(version)
        if template_folder is None:
            AcOutputManager.fail(f"Arches version {version} not supported.")
            exit(1)
        
        target_path = os.path.join(self._get_ac_directory_path(), project_name)
        if os.path.exists(target_path):
            AcOutputManager.fail(f"Project {project_name} already exists.")
            exit(1)

        shutil.copytree(template_folder, target_path)
        project_hash = _generate_project_hash(target_path)
        self._replace_projectname_placeholder(project_name, target_path, repo_name, project_hash)

        # Adjust platform lines for arm64
        if platform.machine() == "arm64" or platform.machine() == "aarch64":
            _adjust_platform_lines(target_path, uncomment=True)
        
        ac_settings = self.get_settings()
        
        if ac_settings.settings["active_project"] == "":
            ac_settings.set_active_project(project_name)
        return target_path, project_hash
        
    def _replace_projectname_placeholder(self, project_name, target_path, repo_name=None, project_hash=""):
        for dname, dirs, files in os.walk(target_path):
            for fname in files:
                fpath = os.path.join(dname, fname)
                with open(fpath) as f:
                    s = f.read()
                s = s.replace(REPLACE_TOKEN, project_name)
                s = s.replace(REPLACE_TOKEN_URLSAFE, self._get_urlsafe_project_name(project_name))
                s = s.replace(REPLACE_TOKEN_REPO, repo_name if repo_name else self._get_urlsafe_project_name(project_name))
                s = s.replace(REPLACE_TOKEN_HASH, project_hash)
                with open(fpath, "w") as f:
                    f.write(s)

    def _get_project_repo_name(self, project_name):
        # get the project and check in the project_repo_directory setting
        project = self.get_project(project_name)
        #check the AcProjectAttributes.PROJECT_REPO_DIRECTORY setting exists as this has been introduced in 1.1.0
        if AcProjectAttributes.PROJECT_REPO_DIRECTORY.value in project._config:
            project_repo_directory = project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value]
        else:
            # if it doesn't exist then it is likely that the repo exists from before using the prject_name as the directory
            # check for the project name in the workspace
            if os.path.exists(os.path.join(self._path, project_name)):
                project_repo_directory = project_name
            else:
                # if the arches_version is less than 8.0, use the project_name as the directory else the urlsafe version
                arches_version = project[AcProjectAttributes.PROJECT_ARCHES_VERSION.value]
                if float(arches_version) < 8.0:
                    project_repo_directory = project_name
                else:
                    project_repo_directory = self._get_urlsafe_project_name(project_name)

            project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] = project_repo_directory
            project.save()
        return project_repo_directory

    def _get_project_repo_path(self, project_name):
        return os.path.join(self._path, self._get_project_repo_name(project_name))

    def _read_project_hash_from_config(self, project_path) -> str:
        config_path = os.path.join(project_path, "config.json")
        if not os.path.exists(config_path):
            return ""

        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            return ""

        return config.get(AcProjectAttributes.PROJECT_HASH.value, "")

    def _replace_text_in_project_files(self, project_path, old_value, new_value):
        if not old_value or old_value == new_value:
            return

        for root, dirs, files in os.walk(project_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue

                if old_value in content:
                    updated_content = content.replace(old_value, new_value)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(updated_content)

    def _confirm(self, prompt_message, prompt_default=None):
        if prompt_default is None:
            AcOutputManager.stop_spinner()
            response = input(prompt_message)
            AcOutputManager.start_spinner()
            return response.strip().lower() == "y"
        return prompt_default

    def _set_project_hash(self, project_name, new_hash):
        project = self.get_project(project_name)
        if not project.supports_project_hash():
            AcOutputManager.fail(f"Project '{project_name}' does not support hash-based naming.")
            exit(1)

        normalized_hash = _normalize_and_validate_project_hash(new_hash)
        old_hash = project.get_project_hash()
        project_path = project.get_project_path()

        self._replace_text_in_project_files(project_path, old_hash, normalized_hash)

        # Ensure config is always updated even when old hash is absent from files.
        project[AcProjectAttributes.PROJECT_HASH.value] = normalized_hash
        project.save()

        return old_hash, normalized_hash


    # PUBLIC METHODS
    
    def list_available_versions(self):
        '''
        Returns a list of dicts sorted newest-first:
            {"version": str, "display_name": str}
        where display_name appends " (unsupported)" for versions < 7.6.
        '''
        versions = []
        for entry in os.scandir(TEMPLATE_PATH):
            if entry.is_dir() and entry.name.startswith("_") and entry.name.endswith("_"):
                versions.append(entry.name.strip("_"))
        versions.sort(key=lambda v: [int(x) for x in v.split(".")], reverse=True)
        return [
            {
                "version": v,
                "display_name": v if _is_version_supported(v) else f"{v} (unsupported)",
            }
            for v in versions
        ]
    
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
        urlsafe_name = self._get_urlsafe_project_name(project_name)
        repo_name = args.repo_name if args.repo_name else urlsafe_name

        target_path, project_hash = self._create_proj_directory(project_name, args.version, repo_name)

        # update the project config
        project = self.get_project(project_name)
        project[AcProjectAttributes.PROJECT_NAME.value] = project_name
        project[AcProjectAttributes.PROJECT_NAME_URLSAFE.value] = urlsafe_name
        project[AcProjectAttributes.PROJECT_REPO_DIRECTORY.value] = repo_name
        if _version_supports_project_hash(args.version):
            project[AcProjectAttributes.PROJECT_HASH.value] = project_hash

        # arg overrides
        if args.organization:
            project[AcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
        if args.branch:
            project[AcProjectAttributes.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
        
        # always save to persist project_hash and any other in-memory changes
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

    def discover_importable_projects(self):
        '''
        Recursively scans the workspace path for directories containing a
        .ac_*/config.json export file. Skips the .arches_containers management
        directory itself.

        Returns a list of dicts:
            {"project_name": str, "repo_path": str, "display_name": str}
        where repo_path is the directory containing the .ac_<project_name> folder
        and display_name is "project_name" for unique entries, or
        "project_name  (relative/path)" when the same project_name appears
        in multiple locations.
        '''
        search_root = self._path
        ac_dir = self._get_ac_directory_path()
        found = []

        for dirpath, dirnames, _ in os.walk(search_root):
            # Skip the .arches_containers management directory
            dirnames[:] = [
                d for d in dirnames
                if os.path.join(dirpath, d) != ac_dir
                and not d.startswith(".ac_")
            ]
            for entry in os.scandir(dirpath):
                if not entry.is_dir() or not entry.name.startswith(".ac_"):
                    continue
                config_path = os.path.join(entry.path, "config.json")
                if not os.path.isfile(config_path):
                    continue
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    project_name = config.get("project_name", "")
                    if project_name:
                        rel = os.path.relpath(dirpath, search_root)
                        found.append({"project_name": project_name, "repo_path": dirpath, "_rel": rel})
                except (OSError, ValueError):
                    pass

        # Compute display_name: add relative path for duplicates
        from collections import Counter
        name_counts = Counter(d["project_name"] for d in found)
        for d in found:
            if name_counts[d["project_name"]] > 1:
                d["display_name"] = f"{d['project_name']}  (./{d['_rel']})"
            else:
                d["display_name"] = d["project_name"]
            del d["_rel"]

        found.sort(key=lambda d: d["display_name"].lower())
        return found


    def get_settings(self):
        '''
        Returns the AcSettings object.
        '''
        return AcSettings(self)

    def is_active_project_running(self) -> bool:
        '''
        Returns True if the active project has any running containers.
        '''
        try:
            settings = self.get_settings()
            if settings.settings["active_project"] == "":
                return False
            active_project = settings.get_active_project()
            if active_project is None:
                return False
            return has_running_project_containers(
                active_project.project_name,
                active_project[AcProjectAttributes.PROJECT_NAME_URLSAFE.value],
            )
        except Exception:
            return False

    def export_project(self, project_name, repo_path, keep_repo_hash=None, prompt_default=None):
        '''
        Exports a project from the .arches-containers folder to the root of a given repo folder.
        '''
        EXPORT_AC_FOLDER = f".ac_{project_name}"

        project = self.get_project(project_name)
        if project is None:
            raise Exception(f"Project {project_name} not found.")
        
        # check that the target repo path exists and is a directory
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            AcOutputManager.fail(f"Export failed. The target repo path '{repo_path}' does not exist or is not a directory.")
            exit(1)

        project_path = project.get_project_path()
        ac_repo_path = os.path.join(repo_path, EXPORT_AC_FOLDER)
        repo_dir_name = os.path.basename(repo_path)
        
        existing_repo_hash = ""
        use_repo_hash = False

        if os.path.exists(ac_repo_path):
            existing_repo_hash = self._read_project_hash_from_config(ac_repo_path)
            project_hash = project.get_project_hash()
            if project_hash and existing_repo_hash:
                if project_hash == existing_repo_hash:
                    use_repo_hash = True
                elif keep_repo_hash is None:
                    use_repo_hash = self._confirm(
                        "The export target already has a hash. Keep the repo hash so teammates can import without creating new Docker objects? (y/n): ",
                        prompt_default,
                    )
                else:
                    use_repo_hash = keep_repo_hash

            if not self._confirm(f"The directory {ac_repo_path} already exists. Proceed? (y/n): ", prompt_default):
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

        if use_repo_hash:
            source_hash = project.get_project_hash()
            if source_hash and existing_repo_hash and source_hash != existing_repo_hash:
                self._replace_text_in_project_files(ac_repo_path, source_hash, existing_repo_hash)
        
        # Modify Docker YAML files
        for root, dirs, files in os.walk(ac_repo_path):
            for file in files:
                if file.endswith(".yml") or file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r+") as f:
                        content = f.read()
                        content = content.replace(f"/.arches_containers/{project_name}", f"/{repo_dir_name}/{EXPORT_AC_FOLDER}")
                        f.seek(0)
                        f.write(content)
                        f.truncate()
                        
        # Always comment out platform lines on export
        _adjust_platform_lines(ac_repo_path, uncomment=False)
        AcOutputManager.success(f"Project {project_name} exported to {ac_repo_path}.")

    def import_project(self, project_name, repo_path, new_hash=None, target_hash=None, prompt_default=None):
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
            if not self._confirm(f"The project {project_name} already exists. Proceed? (y/n): ", prompt_default):
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

        imported_project = self.get_project(project_name)
        if imported_project.supports_project_hash():
            current_hash = imported_project.get_project_hash()
            selected_hash = ""
            if target_hash:
                selected_hash = _normalize_and_validate_project_hash(target_hash)
            elif new_hash is True:
                selected_hash = _generate_new_project_hash(current_hash)
            elif new_hash is None and current_hash:
                if self._confirm(
                    "Generate a new hash for this import? Keeping the existing hash can overwrite another working environment using the same Docker resource names. (y/n): ",
                    prompt_default,
                ):
                    selected_hash = _generate_new_project_hash(current_hash)

            if selected_hash:
                old_hash, applied_hash = self._set_project_hash(project_name, selected_hash)
                if old_hash != applied_hash:
                    AcOutputManager.write(f"> Updated project hash from '{old_hash}' to '{applied_hash}'.")

        AcOutputManager.success(f"Project {project_name} imported from {ac_repo_path}.")

    def rehash_project(self, project_name, target_hash=None):
        project = self.get_project(project_name)
        if not project.supports_project_hash():
            AcOutputManager.fail(f"Project '{project_name}' does not support hash-based naming.")
            exit(1)

        if has_running_project_containers(project.project_name, project[AcProjectAttributes.PROJECT_NAME_URLSAFE.value]):
            AcOutputManager.fail(
                f"Cannot rehash '{project_name}' while containers are running. Run 'act down -p {project_name}' first to avoid orphaned resources."
            )
            exit(1)

        next_hash = _normalize_and_validate_project_hash(target_hash) if target_hash else _generate_new_project_hash(project.get_project_hash())
        old_hash, applied_hash = self._set_project_hash(project_name, next_hash)

        if old_hash == applied_hash:
            AcOutputManager.complete_step(f"Project '{project_name}' already uses hash '{applied_hash}'.")
            return

        AcOutputManager.success(f"Project '{project_name}' rehashed from '{old_hash}' to '{applied_hash}'.")

    
