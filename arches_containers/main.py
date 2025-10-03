import argparse
from rich_argparse import RichHelpFormatter
import os
import webbrowser
from slugify import slugify
from arches_containers import AC_VERSION as arches_containers_version
from arches_containers.manage import compose_project, initialize_project, status
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject, AcProjectSettings
from arches_containers.utils.create_launch_config import generate_launch_config
from arches_containers.utils.logger import AcOutputManager


def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.", formatter_class=RichHelpFormatter)
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project", formatter_class=parser.formatter_class)
    parser_create.add_argument("-p", "--project_name", required=True, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=True, help="The arches version the project will be using (major.minor format)")
    parser_create.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_create.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_create.add_argument("--activate", action="store_true", help="Activate the project after creation.")
    

    # Sub-parser for starting containers
    parser_up = subparsers.add_parser("up", help="Start the project containers", formatter_class=parser.formatter_class)
    parser_up.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_up.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_up.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")
    container_group_up = parser_up.add_mutually_exclusive_group()
    container_group_up.add_argument("--app", action="store_true", help="Only operate on application containers (docker-compose.yml)")
    container_group_up.add_argument("--dep", action="store_true", help="Only operate on dependency containers (docker-compose-dependencies.yml)")

    # Sub-parser for stopping containers
    parser_down = subparsers.add_parser("down", help="Stop the project containers", formatter_class=parser.formatter_class)
    parser_down.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_down.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")
    container_group_down = parser_down.add_mutually_exclusive_group()
    container_group_down.add_argument("--app", action="store_true", help="Only operate on application containers (docker-compose.yml)")
    container_group_down.add_argument("--dep", action="store_true", help="Only operate on dependency containers (docker-compose-dependencies.yml)")

    # Sub-parser for restarting containers
    parser_restart = subparsers.add_parser("restart", help="Restart the project containers (down + up)", formatter_class=parser.formatter_class)
    parser_restart.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_restart.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_restart.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")
    container_group_restart = parser_restart.add_mutually_exclusive_group()
    container_group_restart.add_argument("--app", action="store_true", help="Only operate on application containers (docker-compose.yml)")
    container_group_restart.add_argument("--dep", action="store_true", help="Only operate on dependency containers (docker-compose-dependencies.yml)")

    # Sub-parser for initializing project
    parser_init = subparsers.add_parser("init", help="Initialize the project", formatter_class=parser.formatter_class)
    parser_init.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_init.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")

    # Sub-parser for activating project
    parser_activate = subparsers.add_parser("activate", help="Set a project as the active project", formatter_class=parser.formatter_class)
    parser_activate.add_argument("-p", "--project_name", required=True, help="The name of the project to activate")
    parser_activate.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")

    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects", formatter_class=parser.formatter_class)
    
    # Sub-parser for the delete command
    parser_delete = subparsers.add_parser("delete", help="Delete an existing container project", formatter_class=parser.formatter_class)
    parser_delete.add_argument("-p", "--project_name", required=True, help="The name of the project to delete")
    
    # Sub-parser for the generate-launch-config command
    parser_launch = subparsers.add_parser("generate-debug-config", help="Generate vscode launch.json configuration for the workspace", formatter_class=parser.formatter_class)
    
    # Sub-parser for the export command
    parser_export = subparsers.add_parser("export", help="Export a project to a given repository folder", formatter_class=parser.formatter_class)
    parser_export.add_argument("-p", "--project_name", help="The name of the project to export. Default is the active project.")
    parser_export.add_argument("-r", "--repo_path", help="The path to the repository folder. Default is <workspace directory path>/<project_name>")

    # Sub-parser for the import command
    parser_import = subparsers.add_parser("import", help="Import a project from a given repository folder", formatter_class=parser.formatter_class)
    parser_import.add_argument("-p", "--project_name", required=True, help="The name of the project to import.")
    parser_import.add_argument("-r", "--repo_path", help="The path to the repository folder. Default is <workspace directory path>/<project_name>")

    # Sub-parser for the status command
    parser_status = subparsers.add_parser("status", help="Check container status", formatter_class=parser.formatter_class)

    # Sub-parser for the view command
    parser_view = subparsers.add_parser("view", help="View the active project in a web browser", formatter_class=parser.formatter_class)
    args = parser.parse_args()
    

    ac_workspace = AcWorkspace()
    ac_settings = ac_workspace.get_settings()

    # ========================================================================================================
    if args.command == "create":
        with AcOutputManager("Creating project") as spinner:
            AcOutputManager.write(f"▶️  Creating project: {args.project_name}")
            
            project_name = slugify(args.project_name)
            project = ac_workspace.create_project(project_name, args)
            if args.activate:
                ac_settings.set_active_project(project.project_name)
    # ========================================================================================================
    elif args.command in ["up", "down", "init", "activate", "restart"]:
        if args.project_name == "" and args.command != "activate":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                AcOutputManager.fail("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")

        with AcOutputManager(f"Running {args.command} command for project: {args.project_name}") as spinner:
            AcOutputManager.write(f"▶️  {args.command.capitalize()} command for project: {args.project_name}")
            
            if hasattr(args, 'organization') or hasattr(args, 'branch'):
                ac_project = ac_workspace.get_project(args.project_name)
                if hasattr(args, 'organization') and args.organization:
                    ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
                if hasattr(args, 'branch') and args.branch:
                    ac_project[AcProjectSettings.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
                ac_project.save()

            if hasattr(args, 'verbose') and args.verbose:
                AcOutputManager.pretty_write_args(vars(args))

            if args.command == "activate":
                ac_settings.set_active_project(args.project_name)
                arches_repo_helper.clone_and_checkout_repo(args.project_name, verbose=args.verbose)
                AcOutputManager.complete_step(f"Project '{args.project_name}' set as active.")
            elif args.command == "init":
                arches_repo_helper.clone_and_checkout_repo(args.project_name, verbose=args.verbose)
                initialize_project(args.project_name, args.verbose)
            elif args.command == "restart":
                arches_repo_helper.change_arches_branch(args.project_name, verbose=args.verbose)
                # Determine container type
                container_type = "app" if getattr(args, 'app', False) else "dep" if getattr(args, 'dep', False) else "both"
                # First bring containers down
                compose_project(args.project_name, "down", False, args.verbose, container_type)
                # Then bring them up, with build if requested
                compose_project(args.project_name, "up", getattr(args, 'build', False), args.verbose, container_type)
            else:
                arches_repo_helper.change_arches_branch(args.project_name, verbose=args.verbose)
                # Determine container type
                container_type = "app" if getattr(args, 'app', False) else "dep" if getattr(args, 'dep', False) else "both"
                compose_project(args.project_name, args.command, getattr(args, 'build', False), args.verbose, container_type)

    # ========================================================================================================
    elif args.command == "list":
        AcOutputManager.write("▶️  Arches Container Projects")
        projects = ac_workspace.list_projects()
        if not projects:
            AcOutputManager.write("No projects found.")
            exit(0)

        default_project = ac_settings.get_active_project()
        for project in projects:
            if default_project and project == default_project.project_name:
                AcOutputManager.write(f"   - {project} (active)", color="green")
            else:
                AcOutputManager.write(f"   - {project}")

    # ========================================================================================================
    elif args.command == "delete":
        AcOutputManager.write(f"▶️  Deleting project: {args.project_name}")
        with AcOutputManager(f"Deleting project: {args.project_name}") as spinner:
            ac_workspace.delete_project(args.project_name)
    
    # ========================================================================================================
    elif args.command == "generate-debug-config":
        with AcOutputManager("Generating launch.json") as spinner:
            generate_launch_config()
    
    # ========================================================================================================
    elif args.command == "export":
        AcOutputManager.write("▶️  Exporting project")
        if args.project_name == "" or args.project_name is None:
            try:
                args.project_name = ac_settings.get_active_project_name()
            except Exception as e:
                AcOutputManager.fail("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")
        repo_path = args.repo_path if args.repo_path else os.path.join(ac_workspace.path, args.project_name)
        ac_workspace.export_project(args.project_name, repo_path)
    
    # ========================================================================================================
    elif args.command == "import":
        AcOutputManager.write("▶️  Importing project")
        if args.project_name == "" or args.project_name is None:
            AcOutputManager.fail("Project name is required for import.")

        repo_path = args.repo_path if args.repo_path else os.path.join(ac_workspace.path, args.project_name)
        ac_workspace.import_project(args.project_name, repo_path)
    
    # ========================================================================================================
    elif args.command == "status":
        with AcOutputManager("Checking active project container status") as spinner:
            AcOutputManager.write("▶️  Checking active project container status")
            status()

    # ========================================================================================================
    elif args.command == "view":
        ac_settings = AcWorkspace().get_settings().settings
        host = ac_settings["host"]
        port = ac_settings["port"]
        url = f"http://{host}:{port}/"
        webbrowser.open(url)

    # ========================================================================================================
    else:
        parser.print_help()

if __name__ == "__main__":
    main()