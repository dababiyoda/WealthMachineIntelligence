"""
Database connection management with production-grade features
Includes connection pooling, retry logic, and monitoring
"""
import os
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import DBAPIError, DisconnectionError
from dotenv import load_dotenv
import structlog

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class DatabaseConnection:
    """Enterprise-grade database connection manager"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Configure engine with production settings
        self.engine = create_engine(
            self.database_url,
            # Connection pool settings
            pool_size=20,  # Number of connections to maintain
            max_overflow=40,  # Maximum overflow connections
            pool_timeout=30,  # Timeout for getting connection from pool
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before using
            
            # Performance settings
            echo=False,  # Set to True for SQL debugging
            future=True,  # Use SQLAlchemy 2.0 style
            
            # Connection arguments
            connect_args={
                "connect_timeout": 10,
                "application_name": "wealthmachine_enterprise",
                "options": "-c statement_timeout=30000"  # 30 second statement timeout
            }
        )
        
        # Configure session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False  # Don't expire objects after commit
        )
        
        # Set up event listeners
        self._setup_event_listeners()
        
        logger.info("Database connection initialized", 
                   pool_size=20, 
                   max_overflow=40)
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring and error handling"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """Configure connection on connect"""
            connection_record.info['pid'] = os.getpid()
            logger.debug("Database connection established", pid=os.getpid())
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log when connection is checked out from pool"""
            pid = os.getpid()
            if connection_record.info['pid'] != pid:
                connection_record.connection = connection_proxy.connection = None
                raise DisconnectionError(
                    "Connection record belongs to pid %s, "
                    "attempting to check out in pid %s" %
                    (connection_record.info['pid'], pid)
                )
        
        @event.listens_for(self.engine, "handle_error")
        def receive_handle_error(exception_context):
            """Handle database errors"""
            if isinstance(exception_context.original_exception, DBAPIError):
                logger.error("Database error occurred",
                           error=str(exception_context.original_exception),
                           statement=str(exception_context.statement),
                           parameters=str(exception_context.parameters))
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup
        
        Usage:
            with db.get_session() as session:
                # Use session here
                session.query(Model).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """Create all tables in the database"""
        from .models import Base
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        from .models import Base
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    def get_pool_status(self) -> dict:
        """Get connection pool statistics"""
        pool = self.engine.pool
        return {
            "size": getattr(pool, 'size', lambda: 0)(),
            "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
            "overflow": getattr(pool, 'overflow', lambda: 0)(),
            "total": getattr(pool, 'size', lambda: 0)() + getattr(pool, 'overflow', lambda: 0)()
        }
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self.get_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

# Global database instance
db = DatabaseConnection()

# Convenience function for getting sessions
get_db = db.get_session