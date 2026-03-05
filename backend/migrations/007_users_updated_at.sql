-- Add updated_at column to users table
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

-- Backfill existing rows
UPDATE users SET updated_at = created_at WHERE updated_at IS NULL;
