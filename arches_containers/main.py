import argparse
from rich_argparse import RichHelpFormatter
import os
import webbrowser
from slugify import slugify
from arches_containers import AC_VERSION as arches_containers_version
from arches_containers.manage import compose_project, initialize_project, status, shell_container, logs_container
import arches_containers.utils.arches_repo_helper as arches_repo_helper
from arches_containers.utils.workspace import AcWorkspace, AcSettings, AcProject, AcProjectAttributes, _is_version_supported
from arches_containers.utils.create_launch_config import generate_launch_config
from arches_containers.utils.logger import AcOutputManager


def _interactive_project_select(message, choices):
    """Arrow-key selector. Returns the chosen string, or None if Esc/Ctrl-C is pressed."""
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl

    current = [0]
    selection = [None]
    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        current[0] = (current[0] - 1) % len(choices)

    @kb.add("down")
    def _down(event):
        current[0] = (current[0] + 1) % len(choices)

    @kb.add("enter")
    def _enter(event):
        selection[0] = choices[current[0]]
        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event):
        event.app.exit()

    def render():
        lines = []
        lines.append(("", "  (up/down arrow keys  Enter to confirm  Esc to cancel)\n\n"))
        for i, choice in enumerate(choices):
            if i == current[0]:
                lines.append(("fg:ansigreen bold", f"  > {choice}\n"))
            else:
                lines.append(("", f"    {choice}\n"))
        return lines

    Application(
        layout=Layout(Window(FormattedTextControl(render, focusable=False))),
        key_bindings=kb,
        full_screen=False,
        refresh_interval=0.05,
    ).run()
    return selection[0]


def _prompt_for_text(prompt):
    """Show a simple text-input prompt. Returns the entered string, or None if Esc/Ctrl-C."""
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.key_binding import KeyBindings
    cancelled = [False]
    kb = KeyBindings()

    @kb.add("escape")
    def _esc(event):
        cancelled[0] = True
        event.app.exit(exception=KeyboardInterrupt)

    try:
        value = pt_prompt(prompt, key_bindings=kb).strip()
    except (KeyboardInterrupt, EOFError):
        return None
    return value if value else None


def _warn_if_project_unsupported(project_name, ac_project):
    """Emit a one-line warning if the project uses an unsupported Arches version (< 7.6)."""
    project_version = ac_project._config.get(AcProjectAttributes.PROJECT_ARCHES_VERSION.value, "")
    if project_version and not _is_version_supported(project_version):
        AcOutputManager.warn(f"Project '{project_name}' uses Arches version {project_version} which is no longer actively maintained.")


def main():
    parser = argparse.ArgumentParser(description="Create and manage Arches container projects.", formatter_class=RichHelpFormatter)
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")
    
    # Sub-parser for the create command
    parser_create = subparsers.add_parser("create", help="Create a new container project", formatter_class=parser.formatter_class)
    parser_create.add_argument("-p", "--project_name", required=False, default=None, help="The name of the project. This value will be slugified to lowercase with underscore separators")
    parser_create.add_argument("-v", "--version", "--ver", required=False, default=None, help="The arches version the project will be using (major.minor format)")
    parser_create.add_argument("-r", "--repo_name", help="The name of the local repository folder to create for the project. v7.6 and higher only.")
    parser_create.add_argument("-o", "--organization", default="archesproject", help="The GitHub organization of the arches repo (default: archesproject)")
    parser_create.add_argument("-br", "--branch", help="The branch of the arches repo to use. Default is the 'dev/<version>.x' branch.")
    parser_create.add_argument("--activate", action="store_true", help="Activate the project after creation.")
    

    # Sub-parser for starting containers
    parser_up = subparsers.add_parser("up", help="Start the project containers. Initialises automatically if needed.", formatter_class=parser.formatter_class)
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
    parser_restart.add_argument("-b", "--build", action="store_true", help="Rebuild containers when composing up")
    parser_restart.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")
    container_group_restart = parser_restart.add_mutually_exclusive_group()
    container_group_restart.add_argument("--app", action="store_true", help="Only operate on application containers (docker-compose.yml)")
    container_group_restart.add_argument("--dep", action="store_true", help="Only operate on dependency containers (docker-compose-dependencies.yml)")

    # Sub-parser for activating project
    parser_activate = subparsers.add_parser("activate", help="Set a project as the active project", formatter_class=parser.formatter_class)
    parser_activate.add_argument("-p", "--project_name", required=False, default=None, help="The name of the project to activate. If omitted, an interactive selector is shown.")
    parser_activate.add_argument("-vb", "--verbose", action="store_true", help="Print verbose output during the compose processes")

    # Sub-parser for the list command
    parser_list = subparsers.add_parser("list", help="List all container projects", formatter_class=parser.formatter_class)
    
    # Sub-parser for the delete command
    parser_delete = subparsers.add_parser("delete", help="Delete an existing container project", formatter_class=parser.formatter_class)
    parser_delete.add_argument("-p", "--project_name", required=False, default=None, help="The name of the project to delete. If omitted, an interactive selector is shown.")
    
    # Sub-parser for the generate-launch-config command
    parser_launch = subparsers.add_parser("generate-debug-config", help="Generate vscode launch.json configuration for the workspace", formatter_class=parser.formatter_class)
    
    # Sub-parser for the export command
    parser_export = subparsers.add_parser("export", help="Export a project to a given repository folder", formatter_class=parser.formatter_class)
    parser_export.add_argument("-p", "--project_name", help="The name of the project to export. Default is the active project.")
    parser_export.add_argument("-r", "--repo_path", help="The path to the repository folder if different to the default.")
    parser_export.add_argument("--keep-repo-hash", action="store_true", default=None, help="Keep the existing hash in the destination .ac_<project> folder if one exists.")
    export_prompt_group = parser_export.add_mutually_exclusive_group()
    export_prompt_group.add_argument("--yes", action="store_true", help="Answer yes to export prompts for non-interactive use.")
    export_prompt_group.add_argument("--no", action="store_true", help="Answer no to export prompts for non-interactive use.")

    # Sub-parser for the import command
    parser_import = subparsers.add_parser("import", help="Import a project from a given repository folder", formatter_class=parser.formatter_class)
    parser_import.add_argument("-p", "--project_name", required=False, default=None, help="The name of the project to import. If omitted, importable projects are discovered interactively.")
    parser_import.add_argument("-r", "--repo_path", help="The path to the repository folder if different to the default.")
    import_hash_group = parser_import.add_mutually_exclusive_group()
    import_hash_group.add_argument("--new-hash", action="store_true", default=None, help="Generate a new hash after import.")
    import_hash_group.add_argument("--hash", dest="hash_value", help="Set an explicit 5-character lowercase hex hash after import.")
    import_prompt_group = parser_import.add_mutually_exclusive_group()
    import_prompt_group.add_argument("--yes", action="store_true", help="Answer yes to import prompts for non-interactive use.")
    import_prompt_group.add_argument("--no", action="store_true", help="Answer no to import prompts for non-interactive use.")

    # Sub-parser for the rehash command
    parser_rehash = subparsers.add_parser("rehash", help="Regenerate or set the hash used in Docker resource names", formatter_class=parser.formatter_class)
    parser_rehash.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_rehash.add_argument("--hash", dest="hash_value", help="Set an explicit 5-character lowercase hex hash instead of generating one.")

    # Sub-parser for the status command
    parser_status = subparsers.add_parser("status", help="Check container status", formatter_class=parser.formatter_class)

    # Sub-parser for the shell command
    parser_shell = subparsers.add_parser("shell", help="Open an interactive shell in a project container", formatter_class=parser.formatter_class)
    parser_shell.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_shell.add_argument("-c", "--container", default=None, help="The name of the container to open a shell in. Defaults to the main application container.")
    parser_shell.add_argument("--exec", dest="exec_cmd", default=None, help="A command to run in the container instead of opening an interactive shell. Useful for scripting.")

    # Sub-parser for the logs command
    parser_logs = subparsers.add_parser("logs", help="Show logs for a project container", formatter_class=parser.formatter_class)
    parser_logs.add_argument("-p", "--project_name", default="", help="The name of the project. If excluded, the active project will be used.")
    parser_logs.add_argument("-c", "--container", default=None, help="The name of the container to show logs for. Defaults to the main application container.")
    parser_logs.add_argument("-f", "--follow", action="store_true", help="Follow the log output.")

    # Sub-parser for the view command
    parser_view = subparsers.add_parser("view", help="View the active project in a web browser", formatter_class=parser.formatter_class)
    args = parser.parse_args()
    

    ac_workspace = AcWorkspace()
    ac_settings = ac_workspace.get_settings()

    # ========================================================================================================
    if args.command == "create":
        if args.project_name is None:
            AcOutputManager.write("▶️  Create Project")
            AcOutputManager.write("  Enter a project name (e.g. 'My Arches Project'). This will be slugified to lowercase with underscores (e.g. 'my_arches_project').")
            entered = _prompt_for_text("  Project name: ")
            if entered is None:
                AcOutputManager.write("Creation cancelled.")
                exit(0)
            args.project_name = entered
        if args.version is None:
            version_items = ac_workspace.list_available_versions()
            AcOutputManager.write("  Select an Arches version for your project:")
            selected_version = _interactive_project_select("", [v["display_name"] for v in version_items])
            if selected_version is None:
                AcOutputManager.write("Creation cancelled.")
                exit(0)
            args.version = next(v["version"] for v in version_items if v["display_name"] == selected_version)
        with AcOutputManager("Creating project") as spinner:
            AcOutputManager.write(f"▶️  Creating project: {args.project_name}")
            
            project_name = slugify(args.project_name)
            project = ac_workspace.create_project(project_name, args)
            if args.activate:
                ac_settings.set_active_project(project.project_name)
            if not _is_version_supported(args.version):
                AcOutputManager.warn(f"Arches version {args.version} is no longer actively maintained, so this template may not work as expected and need manual adjustments to fix.")
    # ========================================================================================================
    elif args.command in ["up", "down", "activate", "restart"]:
        if args.command == "restart":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception:
                AcOutputManager.fail("🔴 No active project set. Run 'act activate' to set an active project.")
        elif args.project_name == "" and args.command != "activate":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                AcOutputManager.fail("🔴 No project name passed and no active project set. Run 'arches-containers create' to create a new project.")

        if args.command == "activate" and args.project_name is None:
            projects = ac_workspace.list_projects()
            if not projects:
                AcOutputManager.fail("🔴 No projects found. Run 'act create' to create a new project.")
                exit(1)
            try:
                active_project_name = ac_settings.get_active_project().project_name
            except Exception:
                active_project_name = None
            choices = [
                f"{p} (active)" if p == active_project_name else p
                for p in projects
            ]
            AcOutputManager.write("▶️ Activate Project...")
            selected = _interactive_project_select(
                "",
                choices,
            )
            if selected is None:
                AcOutputManager.write("Selection cancelled.")
                exit(0)
            args.project_name = selected.removesuffix(" (active)")

        with AcOutputManager(f"Running {args.command} command for project: {args.project_name}") as spinner:
            AcOutputManager.write(f"▶️  {args.command.capitalize()} command for project: {args.project_name}")
            
            ac_project = ac_workspace.get_project(args.project_name)
            if hasattr(args, 'organization') and args.organization:
                ac_project[AcProjectAttributes.PROJECT_ARCHES_REPO_ORGANIZATION.value] = args.organization
            if hasattr(args, 'branch') and args.branch:
                ac_project[AcProjectAttributes.PROJECT_ARCHES_REPO_BRANCH.value] = args.branch
            if (hasattr(args, 'organization') and args.organization) or (hasattr(args, 'branch') and args.branch):
                ac_project.save()

            _warn_if_project_unsupported(args.project_name, ac_project)

            if hasattr(args, 'verbose') and args.verbose:
                AcOutputManager.pretty_write_args(vars(args))

            if args.command == "activate":
                ac_settings.set_active_project(args.project_name)
                arches_repo_helper.clone_and_checkout_repo(args.project_name, verbose=args.verbose)
                AcOutputManager.complete_step(f"Project '{args.project_name}' set as active.")
            elif args.command == "up":
                arches_repo_helper.clone_and_checkout_repo(args.project_name, verbose=args.verbose)
                if not ac_project.is_initialised():
                    initialize_project(args.project_name, args.verbose)
                # Determine container type
                container_type = "app" if getattr(args, 'app', False) else "dep" if getattr(args, 'dep', False) else "both"
                compose_project(args.project_name, "up", getattr(args, 'build', False), args.verbose, container_type)
            elif args.command == "restart":
                arches_repo_helper.clone_and_checkout_repo(args.project_name, verbose=args.verbose)
                # Determine container type
                container_type = "app" if getattr(args, 'app', False) else "dep" if getattr(args, 'dep', False) else "both"
                # First bring containers down
                compose_project(args.project_name, "down", False, args.verbose, container_type)
                # Then bring them up, with build if requested
                compose_project(args.project_name, "up", getattr(args, 'build', False), args.verbose, container_type)
            else:
                # down
                container_type = "app" if getattr(args, 'app', False) else "dep" if getattr(args, 'dep', False) else "both"
                compose_project(args.project_name, "down", False, args.verbose, container_type)

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
        if args.project_name is None:
            projects = ac_workspace.list_projects()
            if not projects:
                AcOutputManager.fail("🔴 No projects found. Run 'act create' to create a new project.")
                exit(1)
            try:
                active_project_name = ac_settings.get_active_project().project_name
            except Exception:
                active_project_name = None
            choices = [
                f"{p} (active)" if p == active_project_name else p
                for p in projects
            ]
            AcOutputManager.write("▶️ Delete Project...")
            selected = _interactive_project_select("", choices)
            if selected is None:
                AcOutputManager.write("Selection cancelled.")
                exit(0)
            args.project_name = selected.removesuffix(" (active)")
        confirm = input(f"  Are you sure you want to delete '{args.project_name}'? [y/N] ").strip().lower()
        if confirm != "y":
            AcOutputManager.write("Deletion cancelled.")
            exit(0)
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
        if args.project_name is None or args.project_name == "":
            projects = ac_workspace.list_projects()
            if not projects:
                AcOutputManager.fail("🔴 No projects found. Run 'act create' to create a new project.")
                exit(1)
            try:
                active_project_name = ac_settings.get_active_project().project_name
            except Exception:
                active_project_name = None
            choices = [
                f"{p} (active)" if p == active_project_name else p
                for p in projects
            ]
            selected = _interactive_project_select("Select a project to export:", choices)
            if selected is None:
                AcOutputManager.write("Selection cancelled.")
                exit(0)
            args.project_name = selected.removesuffix(" (active)")
        export_project = ac_workspace.get_project(args.project_name)
        _warn_if_project_unsupported(args.project_name, export_project)
        repo_path = args.repo_path if args.repo_path else ac_workspace._get_project_repo_path(args.project_name)
        prompt_default = True if args.yes else False if args.no else None
        ac_workspace.export_project(
            args.project_name,
            repo_path,
            keep_repo_hash=args.keep_repo_hash,
            prompt_default=prompt_default,
        )
    
    # ========================================================================================================
    elif args.command == "import":
        AcOutputManager.write("▶️  Import project")
        if args.project_name is None or args.project_name == "":
            with AcOutputManager(f"... Discovering importable projects") as spinner:
                AcOutputManager.text("... Discovering importable projects")
                discovered = ac_workspace.discover_importable_projects()
            if not discovered:
                AcOutputManager.fail("🔴 No importable projects found. Ensure the repository folder contains a .ac_<project_name>/config.json file.")
                exit(1)
            choices = [d["display_name"] for d in discovered]
            selected = _interactive_project_select("Select a project to import:", choices)
            if selected is None:
                AcOutputManager.write("Selection cancelled.")
                exit(0)
            match = next(d for d in discovered if d["display_name"] == selected)
            args.project_name = match["project_name"]
            import_repo_path = match["repo_path"]
        else:
            import_repo_path = args.repo_path if args.repo_path else os.path.join(ac_workspace.path, args.project_name)
        repo_path = args.repo_path if args.repo_path else import_repo_path
        prompt_default = True if args.yes else False if args.no else None
        AcOutputManager.write("... Importing project")
        ac_workspace.import_project(
            args.project_name,
            repo_path,
            new_hash=args.new_hash,
            target_hash=args.hash_value,
            prompt_default=prompt_default,
        )

    # ========================================================================================================
    elif args.command == "rehash":
        if args.project_name == "":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                AcOutputManager.fail("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")

        with AcOutputManager(f"Running rehash command for project: {args.project_name}") as spinner:
            AcOutputManager.write(f"▶️  Rehash command for project: {args.project_name}")
            rehash_project = ac_workspace.get_project(args.project_name)
            _warn_if_project_unsupported(args.project_name, rehash_project)
            ac_workspace.rehash_project(args.project_name, target_hash=args.hash_value)
    
    # ========================================================================================================
    elif args.command == "status":
        with AcOutputManager("Checking active project container status") as spinner:
            AcOutputManager.write("▶️  Checking active project container status")
            status()

    # ========================================================================================================
    elif args.command == "shell":
        if args.project_name == "":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                AcOutputManager.fail("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")
        result_code = shell_container(args.project_name, container=args.container, exec_cmd=args.exec_cmd)
        if result_code != 0:
            exit(result_code)

    # ========================================================================================================
    elif args.command == "logs":
        if args.project_name == "":
            try:
                args.project_name = ac_settings.get_active_project().project_name
            except Exception as e:
                AcOutputManager.fail("No project name passed and no active project set. Run 'arches-containers create' to create a new project.")
        result_code = logs_container(args.project_name, container=args.container, follow=args.follow)
        if result_code != 0:
            exit(result_code)

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