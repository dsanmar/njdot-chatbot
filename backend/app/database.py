"""Supabase database client for NJDOT Chatbot."""

from supabase import create_client, Client
from typing import Optional
from .config import config


class Database:
    """Singleton Supabase database client."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._instance is None:
            if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError(
                    "Missing Supabase credentials. "
                    "Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file"
                )

            cls._instance = create_client(
                config.SUPABASE_URL,
                config.SUPABASE_SERVICE_ROLE_KEY,
            )
            print("✅ Supabase client initialized")

        return cls._instance

    @classmethod
    def test_connection(cls) -> bool:
        """Test database connection."""
        try:
            client = cls.get_client()
            client.table("chunks").select("id").limit(1).execute()
            print("✅ Database connection successful")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False


# Convenience function
def get_db() -> Client:
    """Get database client instance."""
    return Database.get_client()


if __name__ == "__main__":
    # Test database connection
    print("🔍 Testing database connection...")
    Database.test_connection()
