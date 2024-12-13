import argparse
from arches_containers.create_ac import handle_create_container_project
from arches_containers.manage_ac import compose_project, initialize_project, list_projects
import arches_containers.install_arches as install_arches_repo
from arches_containers.utils.ac_context import AcSettings

def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project")
    parser_create.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    parser_create.add_argument("--set_default", action="store_true", help="Set the project as the default project. Use with create and manage commands.")
    
    
    # Sub-parser for the manage command
    parser_manage = subparsers.add_parser("manage", help="Manage an existing container project")
    parser_manage.add_argument("-p", "--project_name", default=AcSettings().get_default_project().project_name, help="The name of the project. If excluded, the default project will be used.")
    parser_manage.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_manage.add_argument("-o", "--organization", default=AcSettings().get_default_project()["organization_name"], help="The GitHub organization of the arches repo (default: archesproject)")
    parser_manage.add_argument("--set_default", action="store_true", help="Set the project as the default project. Use with create and manage commands.")
    parser_manage.add_argument("action", choices=["up", "down", "init", "set_default"], help="Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project, 'set_default' to set the project as the default project")
    
    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects")
    
    args = parser.parse_args()
    
    SETTINGS = AcSettings()

    if args.command == "create":
        handle_create_container_project(args)
        if args.set_default:
            SETTINGS.set_default_project(args.project_name)

    elif args.command == "manage":
        if args.action == "set_default":
            SETTINGS.set_default_project(args.project_name)
            print(f"Project '{args.project_name}' set as default.")
            exit(0)

        if args.action == "init":
            install_arches_repo.main(args.project_name, args.organization)
            initialize_project(args.project_name)
        else:
            compose_project(args.project_name, args.action, args.build)
        
        if args.set_default:
            SETTINGS.set_default_project(args.project_name)

    elif args.command == "list":
        list_projects()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()