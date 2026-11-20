#!/bin/sh
set -eu

# Current service migrations are repeatable; rerun them against existing volumes.
export LC_ALL=C
migration_dir=${1:-/migrations}
set -- psql --no-psqlrc --set=ON_ERROR_STOP=1 --single-transaction
found=false
for migration in "$migration_dir"/*.sql; do
    [ -f "$migration" ] || continue
    found=true
    set -- "$@" --file "$migration"
done
if [ "$found" = false ]; then
    echo "No SQL migrations found in $migration_dir" >&2
    exit 1
fi
exec "$@"
