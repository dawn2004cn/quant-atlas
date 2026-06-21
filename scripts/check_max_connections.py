import pymysql

# MySQL connection parameters
config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Default password from config.py
    'database': 'quant_atlas',  # Default database from config.py
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Connect to MySQL
try:
    connection = pymysql.connect(**config)
    with connection.cursor() as cursor:
        # Execute query to get max_connections
        cursor.execute("SHOW VARIABLES LIKE 'max_connections';")
        result = cursor.fetchone()
        print(f"Max connections: {result['Value']}")
finally:
    if connection:
        connection.close()