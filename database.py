import mysql.connector
import os

DB_HOST = os.getenv("postgres.railway.internal", "your-railway-host")
DB_PORT = os.getenv("5432", "3306")
DB_USER = os.getenv("postgres", "your-railway-user")
DB_PASSWORD = os.getenv("MFZHfrYWlnetoIrvsmtNvxsujBMAJZZh", "your-railway-password")
DB_NAME = os.getenv("railway", "your-database-name")

conn = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
