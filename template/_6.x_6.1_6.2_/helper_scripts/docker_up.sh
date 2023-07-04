cd .. && docker-compose -f docker-compose-dependencies.yml -p {{project}} up -d
sleep 30s
# NOTE: --build option can be excluded below if the image does not need rebuilding.
docker-compose -f docker-compose.yml -p {{project}} up -d --build