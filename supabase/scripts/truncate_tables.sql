-- Delete all rows from Flux-Claude canonical tables
-- Uses TRUNCATE with CASCADE to handle foreign key dependencies.

TRUNCATE TABLE
  notification_log,
  messages,
  conversations,
  patterns,
  tasks,
  goals,
  users
RESTART IDENTITY CASCADE;
