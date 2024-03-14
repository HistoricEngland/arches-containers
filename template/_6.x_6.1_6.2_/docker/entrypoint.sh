#!/bin/bash

# APP and YARN folder locations
# ${WEB_ROOT} and ${ARCHES_ROOT} is defined in the Dockerfile, ${ARCHES_PROJECT} in env_file.env
if [[ -z ${ARCHES_PROJECT} ]]; then
	APP_FOLDER=${ARCHES_ROOT}
	PACKAGE_JSON_FOLDER=${ARCHES_ROOT}
else
	APP_FOLDER=${WEB_ROOT}/${ARCHES_PROJECT}
	PACKAGE_JSON_FOLDER=${ARCHES_ROOT}
fi

# SET DEFAULT WORKING DIRECTORY
cd ${APP_FOLDER}

YARN_MODULES_FOLDER=${PACKAGE_JSON_FOLDER}/$(awk \
	-F '--install.modules-folder' '{print $2}' ${PACKAGE_JSON_FOLDER}/.yarnrc \
	| awk '{print $1}' \
	| tr -d $'\r' \
	| tr -d '"' \
	| sed -e "s/^\.\///g")

#Utility functions that check db status
wait_for_db() {
	echo "Testing if database server is up..."
	while [[ ! ${return_code} == 0 ]]
	do
        psql --host=${PGHOST} --port=${PGPORT} --user=${PGUSERNAME} --dbname=postgres -c "select 1" >&/dev/null
		return_code=$?
		sleep 3
	done
	echo "Database server is up"

    echo "Testing if Elasticsearch is up..."
    while [[ ! ${return_code} == 0 ]]
    do
        curl -s "http://${ESHOST}:${ESPORT}/_cluster/health?wait_for_status=green&timeout=60s" >&/dev/null
        return_code=$?
        sleep 3
    done
    echo "Elasticsearch is up"
}

db_exists() {
	echo "Checking if database "${PGDBNAME}" exists..."
	count=`psql --host=${PGHOST} --port=${PGPORT} --user=${PGUSERNAME} --dbname=postgres -Atc "SELECT COUNT(*) FROM pg_catalog.pg_database WHERE datname='${PGDBNAME}'"`

	# Check if returned value is a number and not some error message
	re='^[0-9]+$'
	if ! [[ ${count} =~ $re ]] ; then
	   echo "Error: Something went wrong when checking if database "${PGDBNAME}" exists..." >&2;
	   echo "Exiting..."
	   exit 1
	fi

	# Return 0 (= true) if database exists
	if [[ ${count} > 0 ]]; then
		echo "Checking if database is setup "${PGDBNAME}"..."
		tcount=`psql --host=${PGHOST} --port=${PGPORT} --user=${PGUSERNAME} --dbname=${PGDBNAME} -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'nodes'"`
		# Check if returned value is a number and not some error message
		re='^[0-9]+$'
		if ! [[ ${tcount} =~ $re ]] ; then
		echo "Error: Something went wrong when checking if tables exists in database "${PGDBNAME}"..." >&2;
		echo "Exiting..."
		exit 1
		fi

		# Return 0 (= true) if table exists
		if [[ ${tcount} > 0 ]]; then
			return 0
		else
			return 1
		fi
	else
		return 1
	fi
}


#### Install
init_arches() {
	echo "Checking if Arches project "${ARCHES_PROJECT}" exists..."
	if [[ ! -d ${APP_FOLDER}/${ARCHES_PROJECT} ]] || [[ ! "$(ls ${APP_FOLDER}/${ARCHES_PROJECT})" ]]; then
		echo ""
		echo "----- Custom Arches project '${ARCHES_PROJECT}' does not exist. -----"
		#echo "----- Use the "create_project" command to create the project and then restart the container -----"
		echo ""
		create_arches_project
	else
		echo "Custom Arches project '${ARCHES_PROJECT}' exists."
	fi

	wait_for_db
	if db_exists; then
		echo "Database ${PGDBNAME} already exists."
		echo "Skipping Package Loading"
	else
		echo "Database ${PGDBNAME} does not exists yet."
		run_setup_db #change to run_load_package if preferred 
	fi
}

create_arches_project_only(){
	echo ""
	echo "----- Creating '${ARCHES_PROJECT}'... -----"
	echo ""

	cd ${WEB_ROOT}
	python3 ${WEB_ROOT}/arches/arches/install/arches-project create ${ARCHES_PROJECT}
	APP_FOLDER=${WEB_ROOT}/${ARCHES_PROJECT}
}

create_arches_project() {
	echo "Checking if Arches project "${ARCHES_PROJECT}" exists..."
	if [[ ! -d ${APP_FOLDER}/${ARCHES_PROJECT} ]] || [[ ! "$(ls ${APP_FOLDER}/${ARCHES_PROJECT})" ]]; then
		echo ""
		echo "----- Creating '${ARCHES_PROJECT}'... -----"
		echo ""
		create_arches_project_only
		copy_settings_local
		run_setup_db

		exit_code=$?
		if [[ ${exit_code} != 0 ]]; then
			echo "Something went wrong when creating your Arches project: ${ARCHES_PROJECT}."
			echo "Exiting..."
			exit ${exit_code}
		fi
	else
		echo "Custom Arches project '${ARCHES_PROJECT}' exists."
	fi
}

# Setup Couchdb (when should this happen?)
setup_couchdb() {
    echo "Running: Creating couchdb system databases"
    curl -X PUT ${COUCHDB_URL}/_users
    curl -X PUT ${COUCHDB_URL}/_global_changes
    curl -X PUT ${COUCHDB_URL}/_replicator
}

# Yarn
install_yarn_components() {
	if [[ ! -d ${YARN_MODULES_FOLDER} ]] || [[ ! "$(ls ${YARN_MODULES_FOLDER})" ]]; then
		echo "Yarn modules do not exist, installing..."
		cd ${PACKAGE_JSON_FOLDER}
		yarn install
	fi
}

#### Misc
copy_settings_local() {
	# The settings_local.py in ${ARCHES_ROOT}/arches/ gets ignored if running manage.py from a custom Arches project instead of Arches core app
	echo "Copying ${WEB_ROOT}/docker/settings_local.py to ${APP_FOLDER}/${ARCHES_PROJECT}/settings_local.py..."
	yes | cp ${WEB_ROOT}/docker/settings_local.py ${APP_FOLDER}/${ARCHES_PROJECT}/settings_local.py
}

#### Run commands

start_celery_supervisor() {
	cd ${WEB_ROOT}
	supervisord -c docker/supervisor.conf
}

run_migrations() {
	echo ""
	echo "----- RUNNING DATABASE MIGRATIONS -----"
	echo ""
	cd ${APP_FOLDER}
	python3 manage.py migrate
}

run_setup_db() {
	echo ""
	echo "----- RUNNING SETUP_DB -----"
	echo ""
	if [[ -d ${WEB_ROOT}/${ARCHES_PROJECT}/pkg ]];then
		python3 manage.py packages -o load_package -s ${ARCHES_PROJECT}/pkg -db -dev -y
	else
		cd ${WEB_ROOT}/${ARCHES_PROJECT}
		python3 manage.py setup_db --force
	fi
	setup_couchdb
}

run_load_package() {
	echo ""
	echo "----- *** LOADING PACKAGE: ${ARCHES_PROJECT} *** -----"
	echo ""
	cd ${APP_FOLDER}
	if [[ -d ${ARCHES_PROJECT}/pkg ]];then
		python3 manage.py packages -o load_package -s ${ARCHES_PROJECT}/pkg -db -dev -y
		setup_couchdb
	fi
}

# "exec" means that it will finish building???
run_django_server() {
	echo ""
	echo "----- *** RUNNING DJANGO DEVELOPMENT SERVER *** -----"
	echo ""
	cd ${APP_FOLDER}
    echo "Running Django"
	exec sh -c "pip install debugpy -t /tmp && python3 /tmp/debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:${DJANGO_PORT}"
}

run_livereload_server() {
	echo ""
	echo "----- *** RUNNING LIVERELOAD SERVER *** -----"
	echo ""
	cd ${APP_FOLDER}
    echo "Running livereload"
    exec sh -c "python3 manage.py developer livereload --livereloadhost 0.0.0.0"
}

activate_virtualenv() {
	. ${WEB_ROOT}/ENV/bin/activate
}

#### Main commands
run_arches() {
	init_arches
	install_yarn_components
	run_django_server
}

#### Main commands
run_livereload() {
	run_livereload_server
}

### Starting point ###

# trying not to use virtualenv???
# activate_virtualenv

# Use -gt 1 to consume two arguments per pass in the loop
# (e.g. each argument has a corresponding value to go with it).
# Use -gt 0 to consume one or more arguments per pass in the loop
# (e.g. some arguments don't have a corresponding value to go with it, such as --help ).

# If no arguments are supplied, assume the server needs to be run
if [[ $#  -eq 0 ]]; then
	echo "No arguments supplied, running Arches server..."
	copy_settings_local
	start_celery_supervisor
	wait_for_db
	run_arches
fi

# Else, process arguments
echo "Full command: $@"
while [[ $# -gt 0 ]]
do
	key="$1"
	echo "Command: ${key}"

	case ${key} in
		run_arches)
			copy_settings_local
			wait_for_db
			start_celery_supervisor
			run_arches
		;;
		run_livereload)
			run_livereload_server
		;;
		run_tests)
			copy_settings_local
			wait_for_db
			run_tests
		;;
		run_migrations)
			copy_settings_local
			wait_for_db
			run_migrations
		;;
		create_project)
			create_arches_project_only
		;;
		help|-h)
			display_help
		;;
		*)
            cd ${APP_FOLDER}
			"$@"
			exit 0
		;;
	esac
	shift # next argument or value
done
