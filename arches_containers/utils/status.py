import subprocess
import json
from prettytable import PrettyTable
from arches_containers.utils.logger import AcOutputManager

def get_running_containers(project_name, project_name_urlsafe):
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--format', '{{json .}}'], stdout=subprocess.PIPE, text=True)
        containers = result.stdout.strip().split('\n')
        
        table = PrettyTable()
        table.align = "l"
        table.field_names = ["Name", "State"]
        
        for container in containers:
            container_info = json.loads(container)
            name = container_info['Names']
            status = container_info['Status']
            state = "🟢 Running" if "Up" in status else "🔴 Stopped"
            if project_name in name or project_name_urlsafe in name:
                table.add_row([name, state])

        #if the length of the table is 0, then no containers are running
        if len(table.rows) == 0:
            AcOutputManager.complete_step(f"No {project_name} containers running.")
        else:
            AcOutputManager.write(table)
    except Exception as e:
        AcOutputManager.fail(f"An error occurred fetching status: {e}")