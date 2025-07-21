import psycopg2
import logging
import os
from time import sleep, time

# Configure logging for the script
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

TIMEOUT = 30
INTERVAL = 2


def get_db_config():
    """
    Retrieve PostgreSQL database configuration from environment variables.

    Returns:
        dict: A dictionary containing database configuration values.
    """
    return {
        "dbname": os.environ.get("POSTGRES_DB"),
        "user": os.environ.get("POSTGRES_USER"),
        "password": os.environ.get("POSTGRES_PASSWORD"),
        "host": os.environ.get("POSTGRES_HOST", "db"),  # Default to localhost
        "port": int(os.environ.get("POSTGRES_PORT", 5432)),     # Default to 5432
        "sslmode": os.environ.get("POSTGRES_SSLMODE", "disable"),  # Default to 'disable'
    }


def wait_for_postgres():
    """
    Wait for PostgreSQL to become available by repeatedly trying to connect.

    The function attempts to establish a connection to the PostgreSQL server
    until it succeeds or the timeout is reached.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    logger.info("Waiting for postgres...")
    config = get_db_config()  # Get the database configuration using the function above
    start_time = time()  # Record the start time
    while time() - start_time < TIMEOUT:  # Loop until the timeout is reached
        try:
            with psycopg2.connect(**config) as conn:  # Try to establish a connection using the provided configuration
                logger.info("PostgreSQL is ready!")
                return True  # Return True if the connection was successful
        except psycopg2.OperationalError as error:  # Catch connection errors
            logger.info(
                f"PostgreSQL isn't ready.\npsycopg2 {type(error).__name__}\n{error}\nWaiting for {INTERVAL} second(s)..."
            )
            sleep(INTERVAL)  # Wait for the specified interval before retrying

    logger.error(f"Could not connect to PostgreSQL within {TIMEOUT} seconds.")
    return False  # Return False if the connection was not successful


wait_for_postgres()
