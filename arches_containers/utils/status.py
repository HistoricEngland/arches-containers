import subprocess
import json
from prettytable import PrettyTable
from arches_containers.utils.logger import AcOutputManager


def _list_project_containers(project_name, project_name_urlsafe, running_only=False):
    command = ['docker', 'ps', '--format', '{{json .}}'] if running_only else ['docker', 'ps', '-a', '--format', '{{json .}}']
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
    lines = [line for line in result.stdout.strip().split('\n') if line.strip()]

    containers = []
    for line in lines:
        container_info = json.loads(line)
        name = container_info['Names']
        if project_name in name or project_name_urlsafe in name:
            containers.append(container_info)

    return containers


def has_running_project_containers(project_name, project_name_urlsafe):
    return len(_list_project_containers(project_name, project_name_urlsafe, running_only=True)) > 0

def get_running_containers(project_name, project_name_urlsafe):
    try:
        containers = _list_project_containers(project_name, project_name_urlsafe, running_only=False)
        
        table = PrettyTable()
        table.align = "l"
        table.field_names = ["Name", "State"]
        
        for container in containers:
            name = container['Names']
            status = container['Status']
            state = "🟢 Running" if "Up" in status else "🔴 Stopped"
            table.add_row([name, state])

        #if the length of the table is 0, then no containers are running
        if len(table.rows) == 0:
            AcOutputManager.complete_step(f"No {project_name} containers running.")
        else:
            AcOutputManager.write(table)
    except Exception as e:
        AcOutputManager.fail(f"An error occurred fetching status: {e}")