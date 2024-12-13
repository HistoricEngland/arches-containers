import argparse
from arches_containers.create_ac import handle_create_container_project
from arches_containers.manage_ac import compose_project, initialize_project
import arches_containers.install_arches as install_arches_repo
import arches_containers.utils.ac_context as ac_context

def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project")
    parser_create.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    
    # Sub-parser for the manage command
    parser_manage = subparsers.add_parser("manage", help="Manage an existing container project")
    parser_manage.add_argument("-p", "--project_name", required=True, help="The name of the project")
    parser_manage.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_manage.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the repo (default: archesproject)")
    parser_manage.add_argument("action", choices=["up", "down", "init"], help="Action to perform: 'up' to start the project, 'down' to stop the project, 'init' to initialize the project")
    
    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects")
    
    args = parser.parse_args()
    
    if args.command == "create":
        handle_create_container_project(args)
    elif args.command == "manage":
        if args.action == "init":
            install_arches_repo.main(args.project_name, args.organization)
            initialize_project(args.project_name)
        else:
            compose_project(args.project_name, args.action, args.build)
    elif args.command == "list":
        projects = ac_context.list_ac_projects()
        if projects:
            print("Projects:")
            for project in projects:
                print(f"- {project}")
        else:
            print("No projects found.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()