#!/bin/sh
# Usage:
#   ./db.sh upgrade [revision]   — upgrade (default: head)
#   ./db.sh downgrade <revision> — downgrade to revision or relative (-1, -2, base)
#   ./db.sh current              — show current revision
#   ./db.sh history              — show revision history
#   ./db.sh heads                — show available head revisions

set -e

CMD="${1:-upgrade}"
ARG="${2}"

case "$CMD" in
    upgrade)
        docker compose exec tasks alembic upgrade "${ARG:-head}"
        ;;
    downgrade)
        if [ -z "$ARG" ]; then
            echo "Usage: $0 downgrade <revision|relative>"
            echo "Examples:"
            echo "  $0 downgrade -1        # one step back"
            echo "  $0 downgrade -2        # two steps back"
            echo "  $0 downgrade base      # all the way back"
            echo "  $0 downgrade 0003      # specific revision"
            exit 1
        fi
        docker compose exec tasks alembic downgrade "$ARG"
        ;;
    current)
        docker compose exec tasks alembic current
        ;;
    history)
        docker compose exec tasks alembic history --verbose
        ;;
    heads)
        docker compose exec tasks alembic heads
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Commands: upgrade, downgrade, current, history, heads"
        exit 1
        ;;
esac
