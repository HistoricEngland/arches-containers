docker-compose -f docker-compose-dependencies.yml -p {{project}} up -d
timeout /t 30 /nobreak
docker-compose -f docker-compose.yml -p {{project}} up -d --build