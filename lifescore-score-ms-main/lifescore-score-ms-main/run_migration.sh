#!/bin/sh
echo "Applying the migration..."

# Apply the migration
alembic upgrade head

# Check if the migration application was successful
if [ $? -ne 0 ]; then
  echo "Failed to apply migration."
  exit 1
fi

echo "Migration applied successfully."
