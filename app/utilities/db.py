from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings
from app.utilities.logger import logger
import threading

Base = declarative_base()

# Singleton class for database connection pool
class DatabaseConnectionPool:
    """
    Singleton class for managing a database connection pool.
    
    Attributes:
        databases (dict): A dictionary mapping database names to their URIs.
    """
    _instance = None
    _lock = threading.Lock()
    databases = {'multiagent': settings.sqlserver_uri}

    def __new__(cls):
        """
        Creates a new instance of the DatabaseConnectionPool class.
        
        Returns:
            DatabaseConnectionPool: The singleton instance of the class.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
                    cls._instance._initialize_pools()
        return cls._instance

    def _initialize_pools(self):
        """
        Initializes the database connection pools for the configured databases.
        """
        self._engines = {}
        self._sessions = {}
        for key, uri in self.databases.items():
            try:
                logger.info(f"Key: {key}, URI: {uri}")
                self._engines[key] = create_engine(uri)
                self._sessions[key] = sessionmaker(autocommit=False, autoflush=False, bind=self._engines[key])
            except Exception as e:
                logger.error(f"Failed to initialize database connection pool for {key}: {str(e)}")
    
    def get_session(self, database):
        """
        Retrieves a new session for the specified database.
        
        Parameters:
            database (str): The name of the database for which to get a session.
        
        Returns:
            Session: A new SQLAlchemy session for the specified database.
        
        Raises:
            ValueError: If the specified database is not in the list of available databases.
        """
        if database not in self._sessions:
            raise ValueError(f"Database {database} not in the list of available databases")
        return self._sessions[database]()

    @classmethod
    def get_database_uri(cls, key):
        """
        Retrieves the URI for the specified database.
        
        Parameters:
            key (str): The key for the database whose URI is to be retrieved.
        
        Returns:
            str: The URI of the specified database, or None if not found.
        """
        return cls.databases.get(key, None)

def get_session(database: str):
    """
    Get a database session from the connection pool.

    This function yields a database session for the specified database. 
    It ensures that the session is properly closed after use.

    Args:
        database (str): The name of the database for which to get a session.

    Yields:
        Session: A SQLAlchemy session object for interacting with the database.

    Raises:
        Exception: Any exceptions raised during session creation or closure 
        will propagate to the caller.
    """
    db_pool = DatabaseConnectionPool()
    db = db_pool.get_session(database)
    try:
        yield db
    finally:
        db.close()

def initialize_database():
    """
    Initialize the database by creating all tables defined in the ORM.

    This function sets up the database by creating the necessary tables 
    as defined in the SQLAlchemy ORM models. It logs the initialization 
    process and returns the database engine.

    Returns:
        Engine: A SQLAlchemy engine object connected to the initialized database.

    Raises:
        Exception: Any exceptions raised during the engine creation or 
        table creation will propagate to the caller.
    """
    logger.info("Initializing Database")
    engine = create_engine(DatabaseConnectionPool.get_database_uri('multiagent'))
    Base.metadata.create_all(bind=engine)
    logger.info("Database Initialized")
    return engine