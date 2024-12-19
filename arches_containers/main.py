import argparse
import os
from slugify import slugify
from arches_containers.manage import compose_project, initialize_project
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject, AcProjectSettings
from arches_containers.utils.create_launch_config import generate_launch_config

   

def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project")
    parser_create.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    parser_create.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_create.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_create.add_argument("--activate", action="store_true", help="Activate the project after creation.")
    
    
    # Sub-parser for the manage command
    parser_manage = subparsers.add_parser("manage", help="Manage an existing container project")
    parser_manage.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_manage.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_manage.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_manage.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_manage.add_argument("action", choices=["up", "down", "init", "activate"], help="Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project, 'activate' to set the project as the active project")
    
    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects")
    
    # Sub-parser for the delete command
    parser_delete = subparsers.add_parser("delete", help="Delete an existing container project")
    parser_delete.add_argument("-p", "--project_name", required=True, help="The name of the project to delete")
    
    # Sub-parser for the generate-launch-config command
    parser_launch = subparsers.add_parser("generate-debug-config", help="Generate vscode launch.json configuration for the workspace")
    
    # Sub-parser for the export command
    parser_export = subparsers.add_parser("export", help="Export a project to a given repository folder")
    parser_export.add_argument("-p", "--project_name", help="The name of the project to export. Default is the active project.")
    parser_export.add_argument("-r", "--repo_path", help="The path to the repository folder. Default is <workspace directory path>/<project_name>")

    # Sub-parser for the import command
    parser_import = subparsers.add_parser("import", help="Import a project from a given repository folder")
    parser_import.add_argument("-p", "--project_name", required=True, help="The name of the project to import.")
    parser_import.add_argument("-r", "--repo_path", help="The path to the repository folder. Default is <workspace directory path>/<project_name>")

    args = parser.parse_args()
    ac_workspace = AcWorkspace()
    ac_settings = ac_workspace.get_settings()

    if args.command == "create":
        project_name = slugify(args.project_name)
        project = ac_workspace.create_project(project_name, args)
        if args.activate:
            ac_settings.set_active_project(project.project_name)

    elif args.command == "manage":
        
        if args.project_name == "":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                print("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")
                exit(1)

        ac_project = ac_workspace.get_project(args.project_name)
        if args.organization:
            ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
        if args.branch:
            ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
        ac_project.save()

        if args.action == "activate":
            ac_settings.set_active_project(args.project_name)
            print(f"Project '{args.project_name}' set as active.")
            exit(0)

        if args.action == "init":
            arches_repo_helper.clone_and_checkout_repo(args.project_name)
            initialize_project(args.project_name)
        else:
            compose_project(args.project_name, args.action, args.build)
        

    elif args.command == "list":
        projects = ac_workspace.list_projects()
        if not projects:
            print("No projects found.")
            exit(0)

        print("Projects:")
        default_project = ac_settings.get_active_project()
        for project in projects:
            if default_project and project == default_project.project_name:
                print(f"\033[92m- {project} (active)\033[0m")
            else:
                print(f"- {project}")
    elif args.command == "delete":
        ac_workspace.delete_project(args.project_name)
    
    elif args.command == "generate-debug-config":
        generate_launch_config()
    
    elif args.command == "export":
        if args.project_name == "" or args.project_name is None:
            try:
                args.project_name = ac_settings.get_active_project_name()
            except Exception as e:
                print("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")
                exit(1)
        repo_path = args.repo_path if args.repo_path else os.path.join(ac_workspace.path, args.project_name)
        ac_workspace.export_project(args.project_name, repo_path)
    
    elif args.command == "import":
        if args.project_name == "" or args.project_name is None:
            print("Project name is required for import.")
            exit(1)
        repo_path = args.repo_path if args.repo_path else os.path.join(ac_workspace.path, args.project_name)
        ac_workspace.import_project(args.project_name, repo_path)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()