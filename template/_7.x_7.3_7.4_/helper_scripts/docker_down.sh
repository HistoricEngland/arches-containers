cd .. && docker-compose -f docker-compose.yml -p {{project}} down
docker-compose -f docker-compose-dependencies.yml -p {{project}} down