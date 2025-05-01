import os
import json
from arches_containers.utils.workspace import AcWorkspace
from arches_containers.utils.logger import AcOutputManager


def launch_config():
    return {
            "name": "Debug Arches Project",
            "type": "debugpy",
            "request": "attach",
            "connect": {
              "host": "localhost",
              "port": 5678
            },
            "pathMappings": [
              {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "/web_root"
              }
            ]
          }

def create_launch_config():
    workspace = AcWorkspace().path
    vscode_dir = os.path.join(workspace, ".vscode")
    if not os.path.exists(vscode_dir):
        os.makedirs(vscode_dir)
    launch_json = os.path.join(vscode_dir, "launch.json")
    if os.path.exists(launch_json):
        AcOutputManager.stop_spinner()
        override = input("launch.json already exists. Do you want to override it? (y/n): ")
        AcOutputManager.start_spinner()
        if override.lower() != 'y':
            AcOutputManager.skipped_step("Aborted by user.")
            return
    with open(launch_json, "w") as f:
        json.dump({"configurations": [launch_config()]}, f, indent=4)

def generate_launch_config():
    create_launch_config()
    AcOutputManager.complete_step("launch.json configuration generated successfully.")







