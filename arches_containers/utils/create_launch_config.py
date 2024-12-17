import os
import json
from arches_containers.utils.workspace import AcWorkspace


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
        override = input("launch.json already exists. Do you want to override it? (y/n): ")
        if override.lower() != 'y':
            print("Aborted by user.")
            return
    with open(launch_json, "w") as f:
        json.dump({"configurations": [launch_config()]}, f, indent=4)

def generate_launch_config():
    create_launch_config()
    print("launch.json configuration generated successfully.")







