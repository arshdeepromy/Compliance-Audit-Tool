#!/bin/bash
# =============================================================================
# Tōtika Audit Tool — Deploy / Update / Rollback Script
# Run on Raspberry Pi: ./deploy.sh [update|rollback|status|logs]
# =============================================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$APP_DIR/backups"
DB_PATH="$APP_DIR/instance/totika.db"
COMPOSE="docker compose"

# Colours
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Backup database before any update
# ---------------------------------------------------------------------------
backup_db() {
    mkdir -p "$BACKUP_DIR"
    if [ -f "$DB_PATH" ]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        BACKUP_FILE="$BACKUP_DIR/totika_${TIMESTAMP}_${COMMIT}.db"
        cp "$DB_PATH" "$BACKUP_FILE"
        log "Database backed up to: $BACKUP_FILE"
        # Keep only last 10 backups
        ls -t "$BACKUP_DIR"/totika_*.db 2>/dev/null | tail -n +11 | xargs -r rm
    else
        warn "No database found at $DB_PATH — fresh install"
    fi
}

# ---------------------------------------------------------------------------
# UPDATE — pull latest code, backup DB, rebuild container
# ---------------------------------------------------------------------------
do_update() {
    log "Starting update..."

    # Save current commit hash for rollback
    PREV_COMMIT=$(git rev-parse HEAD)
    echo "$PREV_COMMIT" > "$APP_DIR/.last_good_commit"
    log "Current commit: $(git rev-parse --short HEAD)"

    # Backup database
    backup_db

    # Pull latest code
    log "Pulling latest from GitHub..."
    git stash --quiet 2>/dev/null
    git pull origin main
    git stash pop --quiet 2>/dev/null || true

    NEW_COMMIT=$(git rev-parse --short HEAD)
    log "Updated to commit: $NEW_COMMIT"

    # Rebuild and restart
    log "Rebuilding container..."
    $COMPOSE down
    $COMPOSE up -d --build

    # Wait for container to be healthy
    log "Waiting for app to start..."
    sleep 30

    # Check if container is running (retry up to 3 times)
    RETRIES=3
    RUNNING=false
    for i in $(seq 1 $RETRIES); do
        if $COMPOSE ps | grep -q "running"; then
            RUNNING=true
            break
        fi
        log "Container not ready yet, waiting... (attempt $i/$RETRIES)"
        sleep 10
    done

    if $RUNNING; then
        log "Update successful! App is running on commit $NEW_COMMIT"
        log "Access at: http://$(hostname -I | awk '{print $1}'):5000"
    else
        err "Container failed to start after $RETRIES attempts! Rolling back..."
        do_rollback
    fi
}

# ---------------------------------------------------------------------------
# ROLLBACK — revert to previous commit, restore DB backup
# ---------------------------------------------------------------------------
do_rollback() {
    log "Starting rollback..."

    # Find the commit to roll back to
    if [ -f "$APP_DIR/.last_good_commit" ]; then
        ROLLBACK_COMMIT=$(cat "$APP_DIR/.last_good_commit")
        log "Rolling back to commit: $(echo $ROLLBACK_COMMIT | cut -c1-7)"
    else
        # Fall back to previous commit
        ROLLBACK_COMMIT=$(git rev-parse HEAD~1)
        warn "No saved commit found, rolling back to HEAD~1: $(echo $ROLLBACK_COMMIT | cut -c1-7)"
    fi

    # Stop containers
    $COMPOSE down

    # Restore database from most recent backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/totika_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp "$LATEST_BACKUP" "$DB_PATH"
        log "Database restored from: $(basename $LATEST_BACKUP)"
    else
        warn "No database backup found — keeping current database"
    fi

    # Reset code to previous commit
    git checkout "$ROLLBACK_COMMIT"
    log "Code reverted to: $(git rev-parse --short HEAD)"

    # Rebuild and restart
    $COMPOSE up -d --build

    sleep 5

    if $COMPOSE ps | grep -q "running"; then
        log "Rollback successful! App is running."
        log "Access at: http://$(hostname -I | awk '{print $1}'):5000"
        warn "You are in detached HEAD state. To stay here permanently:"
        warn "  git checkout -b stable-rollback"
        warn "Or to go back to main: git checkout main"
    else
        err "Rollback also failed. Check: docker logs totika-audit-app-web-1"
    fi
}

# ---------------------------------------------------------------------------
# STATUS — show current state
# ---------------------------------------------------------------------------
do_status() {
    echo ""
    log "=== Tōtika Audit Tool Status ==="
    echo ""
    echo "  Git commit:  $(git rev-parse --short HEAD) ($(git log -1 --format='%s' | cut -c1-60))"
    echo "  Git branch:  $(git branch --show-current 2>/dev/null || echo 'detached')"
    echo ""
    echo "  Container:"
    $COMPOSE ps
    echo ""
    if [ -f "$DB_PATH" ]; then
        DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
        echo "  Database:    $DB_PATH ($DB_SIZE)"
    else
        echo "  Database:    not found"
    fi
    echo ""
    BACKUP_COUNT=$(ls "$BACKUP_DIR"/totika_*.db 2>/dev/null | wc -l)
    echo "  Backups:     $BACKUP_COUNT saved in $BACKUP_DIR/"
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        echo "  Latest:      $(ls -t "$BACKUP_DIR"/totika_*.db | head -1 | xargs basename)"
    fi
    echo ""
}

# ---------------------------------------------------------------------------
# LOGS — tail container logs
# ---------------------------------------------------------------------------
do_logs() {
    docker logs totika-audit-app-web-1 --tail 50 -f
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
cd "$APP_DIR"

case "${1:-update}" in
    update)   do_update ;;
    rollback) do_rollback ;;
    status)   do_status ;;
    logs)     do_logs ;;
    *)
        echo "Usage: ./deploy.sh [update|rollback|status|logs]"
        echo ""
        echo "  update    Pull latest code, backup DB, rebuild (default)"
        echo "  rollback  Revert to previous version + restore DB"
        echo "  status    Show current deployment state"
        echo "  logs      Tail container logs (Ctrl+C to stop)"
        ;;
esac
