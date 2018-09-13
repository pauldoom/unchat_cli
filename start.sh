#!/usr/bin/env bash
docker run --network=unchat_default --env-file unchat_cli.env -it unchat-python-cli
