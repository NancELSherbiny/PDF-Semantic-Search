#!/usr/bin/env bash
#
# orchestrate.sh — the single entrypoint for the Docker Compose setup.
# It is deliberately thin: the real configuration lives in docker-compose.yml.
#
#   ./orchestrate.sh --action start       build + launch all containers
#   ./orchestrate.sh --action terminate   stop + remove containers/volumes/networks

# Stop immediately if any command fails, instead of pretending it succeeded.
set -e

# Always run from the script's own folder, so `docker compose` finds
# docker-compose.yml no matter where the script was called from.
cd "$(dirname "$0")"

# The action is the word after "--action", i.e. the 2nd argument.
ACTION="$2"

case "$ACTION" in
    start)
        # --wait blocks until services are healthy, so the command doesn't
        # return before the API can actually accept traffic.
        docker compose up --build -d --wait
        ;;
    terminate)
        docker compose down -v --remove-orphans
        ;;
    *)
        echo "Usage: ./orchestrate.sh --action <start|terminate>"
        exit 1
        ;;
esac
