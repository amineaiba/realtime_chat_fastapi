from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

settings = get_settings()

# Create the Engine
engine = create_engine(settings.DATABASE_URL)

# 3. Create SessionLocal Class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create the Base Class
# All your database models will inherit from this class
Base = declarative_base()


# 5. Dependency: Get DB Session
# This function creates a new session for a request and closes it when done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
