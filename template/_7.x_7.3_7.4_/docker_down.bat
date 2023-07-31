docker-compose -f docker-compose.yml --profile=livereload -p {{project}} down
docker-compose -f docker-compose-dependencies.yml -p {{project}} down