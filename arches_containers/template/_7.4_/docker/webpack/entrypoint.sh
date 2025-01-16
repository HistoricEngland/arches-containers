#! /bin/bash

APP_FOLDER=${WEB_ROOT}/${ARCHES_PROJECT}
run_webpack() {
	echo ""
	echo "----- *** RUNNING WEBPACK DEVELOPMENT SERVER *** -----"
	echo ""
	cd ${APP_FOLDER}
    echo "Running Webpack"
	exec sh -c "wait-for-it {{project_urlsafe}}:${DJANGO_PORT} -t 1200 && cd /web_root/{{project}}/{{project}} && yarn install && yarn start"
}

run_webpack