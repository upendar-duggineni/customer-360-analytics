from src.db_connection import engine

connection = engine.connect()

print("Database Connected Successfully!")

connection.close()