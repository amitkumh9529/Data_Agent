import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class DatabaseUtil:
    def __init__(self, db_config=None):
        self.db_config = db_config if db_config is not None else self.get_db_config_from_env()

    @staticmethod
    def get_db_config_from_env():
        """
        Builds database connection config from environment variables.
        Supports Supabase connection string (DATABASE_URL / SUPABASE_DB_URL)
        or individual host, port, user, password, database variables.
        """
        # 1. Direct connection URI / DSN (common in Supabase Dashboard)
        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        if db_url:
            return db_url

        # 2. Individual connection parameters
        host = os.getenv("host") or os.getenv("SUPABASE_HOST") or os.getenv("DB_HOST", "localhost")
        port = os.getenv("port") or os.getenv("SUPABASE_PORT") or os.getenv("DB_PORT", "5432")
        user = os.getenv("user") or os.getenv("SUPABASE_USER") or os.getenv("DB_USER", "postgres")
        password = os.getenv("password") or os.getenv("SUPABASE_PASSWORD") or os.getenv("DB_PASSWORD", "")
        database = (
            os.getenv("database")
            or os.getenv("dbname")
            or os.getenv("SUPABASE_DATABASE")
            or os.getenv("DB_NAME", "postgres")
        )

        # Supabase enforces SSL connections
        sslmode = os.getenv("sslmode") or ("require" if "supabase" in host.lower() else None)

        config = {
            "host": host,
            "port": int(port),
            "user": user,
            "password": password,
            "dbname": database,
        }
        if sslmode:
            config["sslmode"] = sslmode

        return config

    def get_connection(self):
        """
        Returns a new psycopg2 connection.
        """
        if isinstance(self.db_config, str):
            return psycopg2.connect(self.db_config)

        # Dictionary of parameters
        config = dict(self.db_config)
        # Ensure sslmode is set for Supabase if not specified
        host = str(config.get("host", ""))
        if "supabase" in host.lower() and "sslmode" not in config:
            config["sslmode"] = "require"

        # Handle 'database' vs 'dbname'
        if "database" in config and "dbname" not in config:
            config["dbname"] = config.pop("database")

        return psycopg2.connect(**config)

    def schema_details(self, schema_name="public"):
        """
        Extracts table names, column names, data types, and 5 sample rows
        from the specified PostgreSQL schema for LLM context grounding.
        """
        schema_info_context = f"Database Schema: {schema_name}\n"
        connection = None
        cursor = None

        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # Query all base tables in the schema
            cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """,
                (schema_name,),
            )
            tables_list = cursor.fetchall()

            for table in tables_list:
                table_name = table[0]
                schema_info_context += f"\nTable: {table_name}\n"

                # Adding Columns & Data Types
                cursor.execute(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                    """,
                    (schema_name, table_name),
                )
                columns_list = cursor.fetchall()

                for column in columns_list:
                    column_name = column[0]
                    data_type = column[1]
                    schema_info_context += f"  Column: {column_name}, Data Type: {data_type}\n"

                # Adding Sample Data (up to 5 rows)
                try:
                    cursor.execute(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT 5;')
                    sample_data = cursor.fetchall()
                    schema_info_context += "  Sample Data:\n"
                    for row in sample_data:
                        schema_info_context += f"    {row}\n"
                except Exception as sample_err:
                    schema_info_context += f"  (Could not fetch sample rows: {sample_err})\n"

        except Exception as e:
            print(f"Error fetching schema details: {e}")
            schema_info_context += f"Error fetching schema details: {e}"

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return schema_info_context

    def execute_sql(self, query: str):
        """
        Executes a SQL query against the database and returns the result rows as string.
        """
        connection = None
        cursor = None

        try:
            # Strip markdown formatting if generated by LLM (e.g. ```sql ... ```)
            clean_query = query.strip()
            if clean_query.startswith("```"):
                clean_query = clean_query.strip("`")
                if clean_query.lower().startswith("sql"):
                    clean_query = clean_query[3:].strip()

            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(clean_query)

            if cursor.description:
                result = cursor.fetchall()
            else:
                result = "Query executed successfully (no rows returned)."

            connection.commit()
            return str(result)

        except Exception as e:
            print(f"Error executing query: {e}")
            return f"Error executing query: {e}"

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


if __name__ == "__main__":
    db = DatabaseUtil()
    result = db.schema_details("public")
    print(result)
