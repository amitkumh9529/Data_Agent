import os
import csv
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from utils.database import DatabaseUtil

load_dotenv()

CSV_DIR = os.path.join(os.path.dirname(__file__), "data")


def feed_database():
    print("Connecting to Supabase PostgreSQL database...")
    db_util = DatabaseUtil()
    conn = db_util.get_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    print("Connected successfully!")

    # ============================================================
    # 1. CREATE TABLES & SCHEMAS
    # ============================================================
    create_tables_sql = """
    CREATE SCHEMA IF NOT EXISTS public;

    -- USERS
    CREATE TABLE IF NOT EXISTS public.users (
        user_id INTEGER PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        phone VARCHAR(50),
        city VARCHAR(100),
        province VARCHAR(50),
        user_type VARCHAR(20) NOT NULL,
        signup_date DATE,
        is_active BOOLEAN
    );

    -- VEHICLES
    CREATE TABLE IF NOT EXISTS public.vehicles (
        vehicle_id INTEGER PRIMARY KEY,
        driver_id INTEGER NOT NULL,
        make VARCHAR(50),
        model VARCHAR(50),
        year INTEGER,
        license_plate VARCHAR(20) UNIQUE,
        color VARCHAR(30),
        is_active BOOLEAN,
        CONSTRAINT fk_vehicle_driver FOREIGN KEY (driver_id) REFERENCES public.users(user_id)
    );

    -- RIDES
    CREATE TABLE IF NOT EXISTS public.rides (
        ride_id INTEGER PRIMARY KEY,
        rider_id INTEGER NOT NULL,
        driver_id INTEGER NOT NULL,
        requested_at TIMESTAMP,
        pickup_time TIMESTAMP,
        dropoff_time TIMESTAMP,
        pickup_latitude DECIMAL(9,6),
        pickup_longitude DECIMAL(9,6),
        dropoff_latitude DECIMAL(9,6),
        dropoff_longitude DECIMAL(9,6),
        distance_km DECIMAL(10,2),
        fare DECIMAL(10,2),
        surge_multiplier DECIMAL(4,2),
        status VARCHAR(30),
        cancellation_reason VARCHAR(100),
        CONSTRAINT fk_ride_rider FOREIGN KEY (rider_id) REFERENCES public.users(user_id),
        CONSTRAINT fk_ride_driver FOREIGN KEY (driver_id) REFERENCES public.users(user_id)
    );

    -- PAYMENTS
    CREATE TABLE IF NOT EXISTS public.payments (
        payment_id INTEGER PRIMARY KEY,
        ride_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10,2),
        payment_method VARCHAR(50),
        payment_status VARCHAR(30),
        transaction_id VARCHAR(100) UNIQUE,
        payment_time TIMESTAMP,
        CONSTRAINT fk_payment_ride FOREIGN KEY (ride_id) REFERENCES public.rides(ride_id),
        CONSTRAINT fk_payment_user FOREIGN KEY (user_id) REFERENCES public.users(user_id)
    );

    -- RATINGS
    CREATE TABLE IF NOT EXISTS public.ratings (
        rating_id INTEGER PRIMARY KEY,
        ride_id INTEGER NOT NULL,
        rider_id INTEGER NOT NULL,
        driver_id INTEGER NOT NULL,
        rating INTEGER,
        comment TEXT,
        rated_at TIMESTAMP,
        CONSTRAINT fk_rating_ride FOREIGN KEY (ride_id) REFERENCES public.rides(ride_id),
        CONSTRAINT fk_rating_rider FOREIGN KEY (rider_id) REFERENCES public.users(user_id),
        CONSTRAINT fk_rating_driver FOREIGN KEY (driver_id) REFERENCES public.users(user_id),
        CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
    );

    -- INDEXES
    CREATE INDEX IF NOT EXISTS idx_vehicles_driver_id ON public.vehicles(driver_id);
    CREATE INDEX IF NOT EXISTS idx_rides_rider_id ON public.rides(rider_id);
    CREATE INDEX IF NOT EXISTS idx_rides_driver_id ON public.rides(driver_id);
    CREATE INDEX IF NOT EXISTS idx_rides_requested_at ON public.rides(requested_at);
    CREATE INDEX IF NOT EXISTS idx_rides_status ON public.rides(status);
    CREATE INDEX IF NOT EXISTS idx_payments_ride_id ON public.payments(ride_id);
    CREATE INDEX IF NOT EXISTS idx_payments_user_id ON public.payments(user_id);
    CREATE INDEX IF NOT EXISTS idx_ratings_ride_id ON public.ratings(ride_id);
    CREATE INDEX IF NOT EXISTS idx_ratings_driver_id ON public.ratings(driver_id);
    """

    print("Creating tables and indexes in Supabase...")
    cursor.execute(create_tables_sql)
    conn.commit()
    print("Tables ready.")

    # ============================================================
    # 2. CLEAR EXISTING DATA BEFORE RELOAD
    # ============================================================
    print("Clearing any existing data...")
    cursor.execute("""
        TRUNCATE TABLE
            public.ratings,
            public.payments,
            public.rides,
            public.vehicles,
            public.users
        CASCADE;
    """)
    conn.commit()

    # ============================================================
    # 3. LOAD DATA FROM CSV
    # ============================================================
    def load_csv(table_name, csv_filename, columns):
        file_path = os.path.join(CSV_DIR, csv_filename)
        if not os.path.exists(file_path):
            print(f"Warning: CSV file not found: {file_path}")
            return

        print(f"Loading {csv_filename} into {table_name}...")
        try:
            # Try PostgreSQL COPY FROM STDIN (fastest)
            copy_sql = sql.SQL("""
                COPY {} ({})
                FROM STDIN
                WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',', NULL '')
            """).format(
                sql.Identifier("public", table_name),
                sql.SQL(", ").join(sql.Identifier(col) for col in columns)
            )
            with open(file_path, "r", encoding="utf-8") as f:
                cursor.copy_expert(copy_sql, f)
            conn.commit()
            print(f"Loaded {csv_filename} successfully.")
        except Exception as copy_err:
            print(f"COPY failed ({copy_err}), falling back to row-by-row batch insert...")
            conn.rollback()
            # Fallback batch insert
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    rows.append([None if row[col] == "" else row[col] for col in columns])

                cols_formatted = ", ".join(columns)
                placeholders = ", ".join(["%s"] * len(columns))
                insert_sql = f"INSERT INTO public.{table_name} ({cols_formatted}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
                cursor.executemany(insert_sql, rows)
            conn.commit()
            print(f"Batch inserted {len(rows)} rows into {table_name}.")

    # Load in dependency order (users first, then vehicles/rides, etc.)
    load_csv(
        "users",
        "users.csv",
        ["user_id", "first_name", "last_name", "email", "phone", "city", "province", "user_type", "signup_date", "is_active"]
    )

    load_csv(
        "vehicles",
        "vehicles.csv",
        ["vehicle_id", "driver_id", "make", "model", "year", "license_plate", "color", "is_active"]
    )

    load_csv(
        "rides",
        "rides.csv",
        ["ride_id", "rider_id", "driver_id", "requested_at", "pickup_time", "dropoff_time",
         "pickup_latitude", "pickup_longitude", "dropoff_latitude", "dropoff_longitude",
         "distance_km", "fare", "surge_multiplier", "status", "cancellation_reason"]
    )

    load_csv(
        "payments",
        "payments.csv",
        ["payment_id", "ride_id", "user_id", "amount", "payment_method", "payment_status", "transaction_id", "payment_time"]
    )

    load_csv(
        "ratings",
        "ratings.csv",
        ["rating_id", "ride_id", "rider_id", "driver_id", "rating", "comment", "rated_at"]
    )

    cursor.close()
    conn.close()
    print("\nDatabase seeded successfully in Supabase!")


if __name__ == "__main__":
    feed_database()
