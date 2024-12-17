import argparse
from slugify import slugify
from arches_containers.manage import compose_project, initialize_project
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject, AcProjectSettings

def handle_create_container_project(args):
    WORKSPACE = AcWorkspace()
    

def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project")
    parser_create.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    parser_create.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_create.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_create.add_argument("--set_default", action="store_true", help="Set the project as the default project. Use with create and manage commands.")
    
    
    # Sub-parser for the manage command
    parser_manage = subparsers.add_parser("manage", help="Manage an existing container project")
    parser_manage.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the default project will be used.")
    parser_manage.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_manage.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_manage.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_manage.add_argument("action", choices=["up", "down", "init", "set_default"], help="Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project, 'set_default' to set the project as the default project")
    
    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects")
    
    # Sub-parser for the delete command
    parser_delete = subparsers.add_parser("delete", help="Delete an existing container project")
    parser_delete.add_argument("-p", "--project_name", required=True, help="The name of the project to delete")
    
    args = parser.parse_args()
    WORKSPACE = AcWorkspace()
    SETTINGS = WORKSPACE.get_settings()

    if args.command == "create":
        project_name = slugify(args.project_name)
        project = WORKSPACE.create_project(project_name, args)
        if args.set_default:
            SETTINGS.set_default_project(project.project_name)

    elif args.command == "manage":
        
        if args.project_name == "":
            try:
                args.project_name = SETTINGS.get_default_project().project_name
            except Exception as e:
                print("No project name passed and no default project set. Run 'arches-containers create' to create a new project.")
                exit(1)

        CONFIG = WORKSPACE.get_project(args.project_name)
        if args.organization:
            CONFIG[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
        if args.branch:
            CONFIG[AcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
        CONFIG.save()

        if args.action == "set_default":
            SETTINGS.set_default_project(args.project_name)
            print(f"Project '{args.project_name}' set as default.")
            exit(0)

        if args.action == "init":
            arches_repo_helper.clone_and_checkout_repo(args.project_name)
            initialize_project(args.project_name)
        else:
            compose_project(args.project_name, args.action, args.build)
        

    elif args.command == "list":
        projects = WORKSPACE.list_projects()
        if not projects:
            print("No projects found.")
            exit(0)

        print("Projects:")
        default_project = SETTINGS.get_default_project()
        for project in projects:
            if default_project and project == default_project.project_name:
                print(f"\033[92m- {project} (default)\033[0m")
            else:
                print(f"- {project}")
    elif args.command == "delete":
        WORKSPACE.delete_project(args.project_name)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()