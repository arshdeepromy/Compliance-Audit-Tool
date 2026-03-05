#!/bin/bash
# =============================================================================
# Tōtika Audit Tool — Deploy / Update / Rollback Script
# Run on Raspberry Pi: bash deploy.sh [update|rollback|status|logs]
# =============================================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$APP_DIR/backups"
DB_PATH="$APP_DIR/instance/totika.db"
UPLOADS_DIR="$APP_DIR/uploads"
INSTANCE_DIR="$APP_DIR/instance"
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
# Ensure persistent directories exist on host BEFORE Docker touches them
# ---------------------------------------------------------------------------
ensure_dirs() {
    mkdir -p "$INSTANCE_DIR"
    mkdir -p "$UPLOADS_DIR"
    mkdir -p "$BACKUP_DIR"
}

# ---------------------------------------------------------------------------
# Backup database + uploads before any update
# ---------------------------------------------------------------------------
backup_db() {
    ensure_dirs
    if [ -f "$DB_PATH" ]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        BACKUP_FILE="$BACKUP_DIR/totika_${TIMESTAMP}_${COMMIT}.db"
        # Use sqlite3 .backup if available (safe even while DB is in use)
        if command -v sqlite3 &>/dev/null; then
            sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
        else
            cp "$DB_PATH" "$BACKUP_FILE"
        fi
        log "Database backed up to: $BACKUP_FILE"

        # Backup uploads directory if it has files
        if [ -d "$UPLOADS_DIR" ] && [ "$(ls -A "$UPLOADS_DIR" 2>/dev/null)" ]; then
            UPLOADS_BACKUP="$BACKUP_DIR/uploads_${TIMESTAMP}_${COMMIT}.tar.gz"
            tar -czf "$UPLOADS_BACKUP" -C "$APP_DIR" uploads/
            log "Uploads backed up to: $UPLOADS_BACKUP"
        fi

        # Keep only last 10 DB backups
        ls -t "$BACKUP_DIR"/totika_*.db 2>/dev/null | tail -n +11 | xargs -r rm
        # Keep only last 5 upload backups
        ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm
    else
        warn "No database found at $DB_PATH — fresh install"
    fi
}

# ---------------------------------------------------------------------------
# UPDATE — pull latest code, backup DB, rebuild container
# ---------------------------------------------------------------------------
do_update() {
    log "Starting update..."
    ensure_dirs

    # Save current commit hash for rollback
    PREV_COMMIT=$(git rev-parse HEAD)
    echo "$PREV_COMMIT" > "$APP_DIR/.last_good_commit"
    log "Current commit: $(git rev-parse --short HEAD)"

    # Backup database and uploads FIRST
    backup_db

    # Record DB size before anything changes
    PRE_UPDATE_DB_SIZE=0
    if [ -f "$DB_PATH" ]; then
        PRE_UPDATE_DB_SIZE=$(stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
        log "Database size before update: $PRE_UPDATE_DB_SIZE bytes"
    fi

    # Pull latest code
    log "Pulling latest from GitHub..."
    git stash --quiet 2>/dev/null || true
    git pull origin main
    git stash pop --quiet 2>/dev/null || true

    NEW_COMMIT=$(git rev-parse --short HEAD)
    log "Updated to commit: $NEW_COMMIT"

    # Ensure data directories still exist after git operations
    ensure_dirs

    # NEVER use 'docker compose down' — it can cause data loss
    # Use --build --force-recreate to rebuild in-place
    log "Rebuilding container (in-place, no downtime)..."
    $COMPOSE up -d --build --force-recreate

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
        # Verify database survived the update
        if [ -f "$DB_PATH" ]; then
            POST_UPDATE_DB_SIZE=$(stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
            if [ "$PRE_UPDATE_DB_SIZE" -gt 10000 ] && [ "$POST_UPDATE_DB_SIZE" -lt "$((PRE_UPDATE_DB_SIZE / 2))" ]; then
                err "DATABASE INTEGRITY CHECK FAILED!"
                err "DB shrunk from $PRE_UPDATE_DB_SIZE to $POST_UPDATE_DB_SIZE bytes"
                err "Auto-restoring from backup..."
                _restore_latest_backup
            else
                log "Database OK ($POST_UPDATE_DB_SIZE bytes)"
            fi
        else
            err "Database file MISSING after update!"
            err "Auto-restoring from backup..."
            _restore_latest_backup
        fi
        log "Update successful! App is running on commit $NEW_COMMIT"
        log "Access at: http://$(hostname -I | awk '{print $1}'):5000"
    else
        err "Container failed to start after $RETRIES attempts! Rolling back..."
        do_rollback
    fi
}

# ---------------------------------------------------------------------------
# Restore latest backup (helper)
# ---------------------------------------------------------------------------
_restore_latest_backup() {
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/totika_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        ensure_dirs
        $COMPOSE stop web 2>/dev/null || true
        cp "$LATEST_BACKUP" "$DB_PATH"
        $COMPOSE start web
        sleep 10
        log "Database restored from: $(basename $LATEST_BACKUP)"
    else
        err "No backup available to restore!"
    fi
}

# ---------------------------------------------------------------------------
# ROLLBACK — revert to previous commit, restore DB backup
# ---------------------------------------------------------------------------
do_rollback() {
    log "Starting rollback..."
    ensure_dirs

    # Find the commit to roll back to
    if [ -f "$APP_DIR/.last_good_commit" ]; then
        ROLLBACK_COMMIT=$(cat "$APP_DIR/.last_good_commit")
        log "Rolling back to commit: $(echo $ROLLBACK_COMMIT | cut -c1-7)"
    else
        ROLLBACK_COMMIT=$(git rev-parse HEAD~1)
        warn "No saved commit found, rolling back to HEAD~1: $(echo $ROLLBACK_COMMIT | cut -c1-7)"
    fi

    # Stop container (NOT down — preserve everything)
    $COMPOSE stop web 2>/dev/null || true

    # Restore database from most recent backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/totika_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp "$LATEST_BACKUP" "$DB_PATH"
        log "Database restored from: $(basename $LATEST_BACKUP)"
    else
        warn "No database backup found — keeping current database"
    fi

    # Restore uploads if backup exists
    LATEST_UPLOADS=$(ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | head -1)
    if [ -n "$LATEST_UPLOADS" ]; then
        tar -xzf "$LATEST_UPLOADS" -C "$APP_DIR"
        log "Uploads restored from: $(basename $LATEST_UPLOADS)"
    fi

    # Reset code to previous commit
    git checkout "$ROLLBACK_COMMIT"
    log "Code reverted to: $(git rev-parse --short HEAD)"

    # Rebuild and restart
    $COMPOSE up -d --build --force-recreate

    sleep 15

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
    if [ -d "$UPLOADS_DIR" ]; then
        UPLOAD_COUNT=$(find "$UPLOADS_DIR" -type f 2>/dev/null | wc -l)
        echo "  Uploads:     $UPLOAD_COUNT files in $UPLOADS_DIR/"
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

# Always ensure data directories exist
ensure_dirs

case "${1:-update}" in
    update)   do_update ;;
    rollback) do_rollback ;;
    status)   do_status ;;
    logs)     do_logs ;;
    *)
        echo "Usage: bash deploy.sh [update|rollback|status|logs]"
        echo ""
        echo "  update    Pull latest code, backup DB, rebuild (default)"
        echo "  rollback  Revert to previous version + restore DB"
        echo "  status    Show current deployment state"
        echo "  logs      Tail container logs (Ctrl+C to stop)"
        ;;
esac
