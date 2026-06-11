import sys
from unittest.mock import patch

from arches_containers.main import main


def run_cli(args):
    sys.argv = ["arches-containers"] + args
    try:
        main()
    except SystemExit:
        pass


def test_import_arches_catalog_creates_project_and_clones_repo():
    package = {
        "name": "arches-lingo",
        "project_name": "arches_lingo",
        "kind": "extension",
        "repository": "https://github.com/archesproject/arches-lingo.git",
        "arches_versions": ">=8.0,<=8.1",
        "display_name": "arches-lingo  (extension · Arches >=8.0,<=8.1)",
    }
    templates = [
        {"version": "8.1", "display_name": "8.1"},
        {"version": "8.0", "display_name": "8.0"},
    ]

    with patch("arches_containers.main.fetch_arches_catalog_packages", return_value=[package]), \
         patch("arches_containers.main.get_compatible_template_versions", return_value=templates), \
         patch("arches_containers.main._interactive_project_select", side_effect=[package["display_name"], "8.1 (recommended)"]), \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager"), \
         patch("arches_containers.main.arches_repo_helper.derive_repo_directory_name", return_value="arches-lingo"), \
         patch("arches_containers.main.arches_repo_helper.clone_repository", return_value=True):

        mock_workspace.return_value._get_ac_directory_path.return_value = "/tmp/.arches_containers"
        mock_workspace.return_value.list_available_versions.return_value = templates
        mock_workspace.return_value._confirm.return_value = True
        mock_workspace.return_value.path = "/tmp/workspace"

        run_cli(["import", "-ac"])

        mock_workspace.return_value.create_project.assert_called_once()


def test_import_arches_catalog_exits_when_no_compatible_template():
    package = {
        "name": "arches-lingo",
        "project_name": "arches_lingo",
        "kind": "extension",
        "repository": "https://github.com/archesproject/arches-lingo.git",
        "arches_versions": ">=9.0",
        "display_name": "arches-lingo  (extension · Arches >=9.0)",
    }

    with patch("arches_containers.main.fetch_arches_catalog_packages", return_value=[package]), \
         patch("arches_containers.main.get_compatible_template_versions", return_value=[]), \
         patch("arches_containers.main._interactive_project_select", return_value=package["display_name"]), \
         patch("arches_containers.main.AcWorkspace") as mock_workspace, \
         patch("arches_containers.main.AcOutputManager") as mock_output:

        mock_workspace.return_value._get_ac_directory_path.return_value = "/tmp/.arches_containers"
        mock_workspace.return_value.list_available_versions.return_value = [{"version": "8.1", "display_name": "8.1"}]
        mock_output.fail.side_effect = SystemExit(1)

        run_cli(["import", "-ac"])

        mock_workspace.return_value.create_project.assert_not_called()
