import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

# Lấy cấu hình từ file .env
SERVER = os.getenv('DB_SERVER')
DATABASE = os.getenv('DB_DATABASE')

# Chuỗi kết nối
CONN_STR = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SERVER};'
    f'DATABASE={DATABASE};'
    f'Trusted_Connection=yes;'
)

def get_db_connection():
    try:
        conn = pyodbc.connect(CONN_STR)
        return conn
    except pyodbc.Error as e:
        print(f"❌ Lỗi kết nối Database: {e}")
        raise e