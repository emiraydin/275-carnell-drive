#!/bin/bash
# Upload script to sync assets folder to Cloudflare R2 bucket
# Usage: ./upload-r2.sh [account-id]

ACCOUNT_ID="$1"
BUCKET_NAME="275-carnell-drive"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/assets"

if [ ! -d "$ASSETS_DIR" ]; then
  echo "Error: Directory $ASSETS_DIR does not exist."
  exit 1
fi

echo "Uploading files from $ASSETS_DIR to Cloudflare R2 bucket '$BUCKET_NAME'..."

if [ -n "$ACCOUNT_ID" ]; then
  echo "Using AWS CLI with R2 Endpoint..."
  aws s3 sync "$ASSETS_DIR" "s3://$BUCKET_NAME" --endpoint-url "https://$ACCOUNT_ID.r2.cloudflarestorage.com"
else
  echo "Using Cloudflare Wrangler CLI..."
  npx wrangler r2 object put "$BUCKET_NAME" --file-path="$ASSETS_DIR"
fi

echo "Upload complete!"
