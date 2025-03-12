import mysql.connector
import os

DB_HOST = os.getenv("DB_HOST", "postgres.railway.internal")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "MFZHfrYWlnetoIrvsmtNvxsujBMAJZZh")
DB_NAME = os.getenv("DB_NAME", "railway")

conn = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
