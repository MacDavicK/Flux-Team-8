-- Delete all rows from Flux MVP tables
-- Uses TRUNCATE with CASCADE to handle foreign key dependencies in one pass

TRUNCATE users CASCADE;
