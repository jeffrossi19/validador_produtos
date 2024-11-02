import psycopg2

class DatabaseConnection:
    def __init__(self, db_config, username, password):
        self.db_config = db_config
        self.username = username
        self.password = password

    def __enter__(self):
        self.conn = psycopg2.connect(
            dbname=self.db_config["dbname"],
            user=self.username,
            password=self.password,
            host=self.db_config["host"],
            options=self.db_config["options"],
        )
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()