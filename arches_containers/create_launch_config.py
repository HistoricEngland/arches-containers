import os
import json
from arches_containers.utils.ac_context import AcSettings


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


# in the get_ac_context path create a .vscode directory with a launch.json file if it doesn't already exist
def create_launch_config():
    ac_context = AcSettings().get_ac_context()
    vscode_dir = os.path.join(ac_context, ".vscode")
    if not os.path.exists(vscode_dir):
        os.makedirs(vscode_dir)
    launch_json = os.path.join(vscode_dir, "launch.json")
    if not os.path.exists(launch_json):
        with open(launch_json, "w"):
            pass
    else:
        with open(launch_json, "r") as f:
            launch_config = json.load(f)
            
            if launch_config is None:
                launch_config = {"configurations": []}
            
            if not "configurations" in launch_config:
                launch_config["configurations"] = []
            
            launch_config["configurations"].append(launch_config())

        with open(launch_json, "w") as f:
            json.dump(launch_config, f, indent=4)







