import pymysql
import os

def init_db():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='NewPassword123!',
        autocommit=True
    )
    
    with conn.cursor() as cursor:
        with open('schema.sql', 'r') as f:
            sql_script = f.read()
            
        # Split by semicolon and execute
        commands = [c.strip() for c in sql_script.split(';') if c.strip()]
        for command in commands:
            cursor.execute(command)
            
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
