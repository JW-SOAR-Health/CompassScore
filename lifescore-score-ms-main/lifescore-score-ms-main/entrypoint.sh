#!/bin/sh

echo 'Waiting for 5 seconds before checking database connectivity...'
sleep 5

echo 'Checking database connectivity...'
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"
echo "POSTGRES_USER: $POSTGRES_USERNAME"
echo "POSTGRES_DB: $POSTGRES_NAME"
echo "POSTGRES_PASSWORD: [REDACTED]"

timeout=120
elapsed=0
attempt=1
max_attempts=10

echo "Attempting to connect to Docker database."

while [ "$attempt" -le "$max_attempts" ]; do
    echo "Attempt $attempt: Checking if db host is reachable..."
    if nc -z $POSTGRES_HOST $POSTGRES_PORT; then
        echo "db host is reachable. Checking PostgreSQL connectivity..."
        if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" -d "$POSTGRES_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            echo "Successfully connected to PostgreSQL!"
            break
        else
            error_message=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" -d "$POSTGRES_NAME" -c "SELECT 1;" 2>&1)
            echo "Connection failed. Error: $error_message"
        fi
    else
        echo "db host is not reachable yet."
    fi

    if [ "$elapsed" -ge "$timeout" ]; then
        echo "Timed out waiting for PostgreSQL after ${timeout} seconds"
        exit 1
    fi

    sleep_time=$((attempt * 5))
    echo "Unable to connect to PostgreSQL. Retrying in ${sleep_time} seconds... (${elapsed}s elapsed)"
    sleep $sleep_time
    elapsed=$((elapsed + sleep_time))
    attempt=$((attempt + 1))
done

if [ "$attempt" -gt "$max_attempts" ]; then
    echo "Failed to connect to PostgreSQL after $max_attempts attempts"
    exit 1
fi

echo "Database connection successful!"

if [ "$ENVIRONMENT" != "development" ]; then
    echo 'Running database migrations for non-development environment...'
    cd app/shared_db
    chmod +x run_migration.sh
    ./run_migration.sh
    cd ../../
else
    echo 'Skipping migrations in development environment...'
fi

echo "Migration applied successfully."

echo "Seeding..."
# Run the notification template seeding script
python -m app.shared_db.seeds.seed_all

echo "Starting the application..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
