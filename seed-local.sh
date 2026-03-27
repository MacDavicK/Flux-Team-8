docker run --rm --network=host postgres:15-alpine \
    psql "postgresql://postgres:postgres@localhost:54322/postgres"
  \                                                               
    -f backend/scripts/seed-local.sql