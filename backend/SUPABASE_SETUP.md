# Supabase Setup Guide for Flux AI

This guide will help you set up Supabase as your database for the Flux Agentic AI project.

## Prerequisites

- A Supabase account (sign up at <https://supabase.com>)
- Python environment set up

## Step 1: Create a Supabase Project

1. Go to <https://supabase.com> and sign in
2. Click "New Project"
3. Fill in the project details:
   - **Name**: flux-ai (or your preferred name)
   - **Database Password**: Choose a strong password (save this!)
   - **Region**: Choose the closest region to you
4. Click "Create new project"
5. Wait for the project to be provisioned (takes ~2 minutes)

## Step 2: Get Your Connection Details

### Option A: Direct PostgreSQL Connection (Recommended)

1. In your Supabase dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection String** section
3. Select **URI** tab
4. Copy the connection string that looks like:

   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

5. Replace `[YOUR-PASSWORD]` with your actual database password

### Option B: Supabase Client (Optional - for additional features)

1. Go to **Settings** → **API**
2. Copy:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: Your public API key

## Step 3: Configure Your .env File

1. Copy `.env.example` to `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` and update these values:

   ```bash
   # Supabase Database Configuration
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=your_supabase_anon_key_here
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.your-project-ref.supabase.co:5432/postgres
   
   # OpenAI Configuration
   OPENAI_API_KEY=your_actual_openai_api_key
   ```

## Step 4: Install Dependencies

Install the required packages including PostgreSQL driver:

```powershell
pip install sqlalchemy psycopg2-binary supabase alembic
```

Or install all dependencies:

```powershell
pip install -r requirements.txt
```

## Step 5: Initialize the Database

Run the application to create all tables automatically:

```powershell
python main.py
```

Or run the verify script:

```powershell
python verify_setup.py
```

The tables will be automatically created in your Supabase database!

## Step 6: Verify Database Tables

1. Go to your Supabase dashboard
2. Click on **Table Editor** in the left sidebar
3. You should see the following tables:
   - `goals`
   - `milestones`
   - `tasks`
   - `calendar_events`
   - `notifications`

## Database Schema

The following tables will be created:

### goals

- id (integer, primary key)
- user_id (string)
- title (string)
- description (text)
- due_date (timestamp)
- status (enum: pending, in_progress, completed, paused)
- ai_analysis (text)
- created_at (timestamp)
- updated_at (timestamp)

### milestones

- id (integer, primary key)
- goal_id (foreign key → goals.id)
- title (string)
- description (text)
- week_number (integer)
- target_date (timestamp)
- completed (boolean)
- created_at (timestamp)

### tasks

- id (integer, primary key)
- goal_id (foreign key → goals.id)
- milestone_id (foreign key → milestones.id)
- title (string)
- description (text)
- scheduled_date (timestamp)
- duration_minutes (integer)
- status (enum: scheduled, in_progress, completed, rescheduled, missed)
- completed_at (timestamp)
- created_at (timestamp)

### calendar_events

- id (integer, primary key)
- task_id (foreign key → tasks.id)
- event_id (string)
- start_time (timestamp)
- end_time (timestamp)
- created_at (timestamp)

### notifications

- id (integer, primary key)
- task_id (foreign key → tasks.id)
- scheduled_time (timestamp)
- sent (boolean)
- acknowledged (boolean)
- dismissed (boolean)
- created_at (timestamp)

## Troubleshooting

### Connection Issues

If you can't connect to Supabase:

1. **Check your password**: Make sure you're using the correct database password
2. **Check the connection string format**: Should be:

   ```
   postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
   ```

3. **Test connection**: Use the Supabase SQL Editor to run a simple query
4. **Firewall**: Ensure your firewall allows outbound connections on port 5432

### SSL/TLS Issues

If you encounter SSL errors, modify your DATABASE_URL:

```bash
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres?sslmode=require
```

### Migration Issues

If you need to reset the database:

1. Go to Supabase dashboard → SQL Editor
2. Run:

   ```sql
   DROP TABLE IF EXISTS notifications CASCADE;
   DROP TABLE IF EXISTS calendar_events CASCADE;
   DROP TABLE IF EXISTS tasks CASCADE;
   DROP TABLE IF EXISTS milestones CASCADE;
   DROP TABLE IF EXISTS goals CASCADE;
   ```

3. Restart your application to recreate tables

## Using Supabase Features

### Real-time Subscriptions (Optional)

Supabase supports real-time subscriptions. You can enable this for your tables:

1. Go to **Database** → **Replication**
2. Enable replication for the tables you want to subscribe to
3. Use Supabase client to subscribe to changes

### Row Level Security (Optional)

For production, enable Row Level Security (RLS):

1. Go to **Authentication** → **Policies**
2. Enable RLS for each table
3. Create policies to control access

Example policy:

```sql
-- Allow users to only see their own goals
CREATE POLICY "Users can view own goals" ON goals
  FOR SELECT USING (auth.uid() = user_id);
```

### Backups

Supabase automatically backs up your database:

- Free tier: Daily backups (7 days retention)
- Pro tier: Point-in-time recovery

## Advantages of Using Supabase

✅ **Managed PostgreSQL** - No server maintenance required
✅ **Auto-scaling** - Handles traffic spikes automatically
✅ **Built-in Auth** - Easy user authentication (future feature)
✅ **Real-time** - Subscribe to database changes
✅ **Storage** - Built-in file storage for future features
✅ **Free Tier** - 500MB database, 2GB bandwidth
✅ **Dashboard** - Easy table management and SQL editor

## Next Steps

1. Set up your `.env` file with Supabase credentials
2. Install dependencies
3. Run the application
4. Test creating a goal through the API
5. Check the data in Supabase dashboard

For more information, visit: <https://supabase.com/docs>
