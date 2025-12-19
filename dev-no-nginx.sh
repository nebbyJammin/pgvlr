#!/usr/bin/bash

docker compose -f docker-compose.yml up --build -d --force-recreate db private_api
