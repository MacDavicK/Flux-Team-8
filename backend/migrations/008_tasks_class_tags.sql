-- Add class_tags to tasks table (mirrors goals.class_tags)
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS class_tags TEXT[] DEFAULT '{}';
