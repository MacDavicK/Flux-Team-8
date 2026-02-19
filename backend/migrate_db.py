"""
Database migration script for Supabase setup.
Run this script to create all necessary tables in your Supabase database.
"""
from database import engine, Base, init_db
from models import Goal, Milestone, Task, CalendarEvent, Notification
import sys

def create_tables():
    """Create all tables in the database."""
    try:
        print("🔄 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        print("\nTables created:")
        print("  - goals")
        print("  - milestones")
        print("  - tasks")
        print("  - calendar_events")
        print("  - notifications")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def drop_tables():
    """Drop all tables from the database."""
    try:
        print("⚠️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully!")
        return True
    except Exception as e:
        print(f"❌ Error dropping tables: {str(e)}")
        return False

def reset_database():
    """Drop and recreate all tables."""
    print("🔄 Resetting database...")
    if drop_tables():
        return create_tables()
    return False

def test_connection():
    """Test database connection."""
    try:
        print("🔄 Testing database connection...")
        connection = engine.connect()
        connection.close()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\nPlease check:")
        print("  1. Your DATABASE_URL in .env file")
        print("  2. Your Supabase project is running")
        print("  3. Your database password is correct")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration script for Supabase")
    parser.add_argument(
        "action",
        choices=["create", "drop", "reset", "test"],
        help="Action to perform: create (create tables), drop (drop tables), reset (drop and create), test (test connection)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Flux AI - Supabase Database Migration")
    print("=" * 60)
    print()
    
    if args.action == "test":
        success = test_connection()
    elif args.action == "create":
        if test_connection():
            success = create_tables()
        else:
            success = False
    elif args.action == "drop":
        if test_connection():
            confirm = input("⚠️  Are you sure you want to drop all tables? (yes/no): ")
            if confirm.lower() == "yes":
                success = drop_tables()
            else:
                print("❌ Operation cancelled")
                success = False
        else:
            success = False
    elif args.action == "reset":
        if test_connection():
            confirm = input("⚠️  Are you sure you want to reset the database? (yes/no): ")
            if confirm.lower() == "yes":
                success = reset_database()
            else:
                print("❌ Operation cancelled")
                success = False
        else:
            success = False
    
    print()
    print("=" * 60)
    sys.exit(0 if success else 1)
