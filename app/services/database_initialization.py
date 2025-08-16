
import mysql.connector
from mysql.connector import Error
import logging
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )

        cursor = connection.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME}")
        logger.info(f"Database '{settings.DB_NAME}' created or already exists")

        # Set charset
        cursor.execute(f"ALTER DATABASE {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Database charset set to utf8mb4")

        cursor.close()
        connection.close()

        return True

    except Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def test_database_connection():
    """Test the database connection"""
    try:
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        if result:
            logger.info("Database connection test successful")
            return True
        return None

    except Error as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def initialize_database():
    """Initialize the complete database setup"""
    logger.info("Starting database initialization...")

    # Step 1: Create database
    if not create_database():
        logger.error("Failed to create database")
        return False

    # Step 2: Test connection
    if not test_database_connection():
        logger.error("Database connection test failed")
        return False

    # Step 3: Create tables using SQLAlchemy
    try:
        from app.models.database import create_tables
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False

    logger.info("Database initialization completed successfully!")
    return True


def check_database_status():
    """Check the current status of the database"""
    logger.info("Checking database status...")

    try:
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

        cursor = connection.cursor()

        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        logger.info(f"Found {len(tables)} tables in database:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            logger.info(f"  - {table[0]}: {count} records")

        cursor.close()
        connection.close()

        return True

    except Error as e:
        logger.error(f"Error checking database status: {e}")
        return False


if __name__ == "__main__":
    print("🗄️  Shopify Insights Database Initialization")
    print("=" * 50)

    # Check if database already exists and has data
    if test_database_connection():
        print(" Database connection successful")
        check_database_status()

        response = input("\nDatabase already exists. Recreate? (y/N): ")
        if response.lower() != 'y':
            print("Skipping database initialization.")
            exit(0)

    # Initialize database
    if initialize_database():
        print("\n Database initialization completed successfully!")
        print(f" Database: {settings.DB_NAME}")
        print(f" Host: {settings.DB_HOST}:{settings.DB_PORT}")
        print("\n You can now start the application with:")
        print("   uvicorn app.main:app --reload --port 8000")
    else:
        print("\n Database initialization failed!")
        print("Please check your MySQL configuration and try again.")
        exit(1)