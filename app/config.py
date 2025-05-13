

"""
Configuration module for the Basketball Stats Tracker application.
Loads environment variables and provides configuration classes for different environments.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()



class Config:
    """
    Base configuration for the application.
    Loads settings from environment variables, with sensible defaults for development.

    Attributes:
        DATABASE_URL (str): Database connection string.
        SECRET_KEY (str): Secret key for Flask session security.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/league_stats.db")
    _secret_key = os.getenv("SECRET_KEY")
    if _secret_key is None:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Please set it in your .env file or environment."
        )
    SECRET_KEY: str = _secret_key
    # Add more config variables as needed

# Optionally, you can define subclasses for different environments

class DevelopmentConfig(Config):
    """
    Configuration for development environment.
    Sets DEBUG to True.
    """
    DEBUG: bool = True


class ProductionConfig(Config):
    """
    Configuration for production environment.
    Sets DEBUG to False.
    """
    DEBUG: bool = False
