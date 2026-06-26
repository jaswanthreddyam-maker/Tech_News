#!/bin/bash
set -e

echo "Running full pytest suite..."
# APP_ENV=test is already set via the test target or explicit export, but we enforce it here
docker compose exec -e APP_ENV=test backend pytest

echo "Verifying development database remains uncontaminated..."
COUNT=$(docker compose exec -T db psql -U postgres -d tech_news_today -t -c "SELECT COUNT(*) FROM sources WHERE url LIKE '%test.com%' OR url LIKE '%example.com%' OR name LIKE 'Test Source%';" | xargs)

if [ "$COUNT" -eq "0" ]; then
    echo "✅ SUCCESS: No synthetic test sources leaked into development database."
else
    echo "❌ FAILURE: Found $COUNT synthetic test sources in development database."
    echo "Check your test suite for un-mocked database inserts or missing cleanups."
    exit 1
fi

echo "Verifying no test users leaked..."
USER_COUNT=$(docker compose exec -T db psql -U postgres -d tech_news_today -t -c "SELECT COUNT(*) FROM users WHERE email LIKE '%@test.local%';" | xargs)

if [ "$USER_COUNT" -eq "0" ]; then
    echo "✅ SUCCESS: No synthetic test users leaked into development database."
    exit 0
else
    echo "❌ FAILURE: Found $USER_COUNT synthetic test users in development database."
    exit 1
fi
