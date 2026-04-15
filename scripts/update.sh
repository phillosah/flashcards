#!/bin/bash
# update.sh — Pull latest code from git and restart FlashCards
# Usage: bash /srv/flashcards/scripts/update.sh
#
# Data file lives at /var/lib/flashcards/data.json (outside the repo)
# so git pull never touches live data.

set -e

APP_DIR="/srv/flashcards"
SERVICE="flashcards"

echo "==> Pulling latest changes..."
cd "$APP_DIR"
git pull origin master

echo "==> Restarting service..."
sudo systemctl restart "$SERVICE"

echo "==> Status:"
sudo systemctl status "$SERVICE" --no-pager -l

echo ""
echo "Done. App is live."
