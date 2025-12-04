#!/usr/bin/bash

docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d --force-recreate db private_api
