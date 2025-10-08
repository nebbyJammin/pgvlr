@echo off
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d db private_api
