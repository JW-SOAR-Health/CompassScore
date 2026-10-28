#!/bin/sh

# Check if a migration message was provided
if [ -z "$1" ]; then
  echo "Usage: $0 'Migration message'"
  exit 1
fi

MIGRATION_MESSAGE=$1

echo "Generating new migration with message: $MIGRATION_MESSAGE"

# Generate the new migration
alembic revision --autogenerate -m "$MIGRATION_MESSAGE"

# Check if the migration generation was successful
if [ $? -ne 0 ]; then
  echo "Failed to generate migration."
  exit 1
fi

echo "Migration generated"
