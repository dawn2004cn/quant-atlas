from app.infrastructure.repositories.mysql.mysql_basic_market_data_repository import MySQLBasicMarketDataRepository
from app.infrastructure.database.db_manager import get_session
from app.infrastructure.database.mysql_settings import MysqlSettings
import os

def check_db_data():
    # Load settings from environment or default
    ms = MysqlSettings(
        host=os.getenv("MYSQL_HOST", "192.168.8.103"),
        port=int(os.getenv("MYSQL_PORT", 3307)),
        database=os.getenv("MYSQL_DATABASE", "quant_atlas"),
        user=os.getenv("MYSQL_USER", "quant_atlas"),
        password=os.getenv("MYSQL_PASSWORD", "")
    )
    
    # Use a lambda to pass the initialized ms to get_session
    session_factory = lambda: get_session(ms)
    repo = MySQLBasicMarketDataRepository(session_factory=session_factory)
    
    try:
        count = repo.count_longhu_rows()
        print(f"Total longhu rows in MySQL: {count}")
    except Exception as e:
        print(f"Error checking MySQL data: {e}")

if __name__ == '__main__':
    check_db_data()
