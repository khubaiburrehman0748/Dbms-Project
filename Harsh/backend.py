import mysql.connector
from mysql.connector import Error

class RailwayBackend:
    def __init__(self):
        # --- MYSQL CONFIGURATION ---
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '^!88Rn53', # Updated to the user's MySQL Workbench password
        }
        self.db_name = 'railway_db'
        self.init_database()

    def get_connection(self):
        """Creates a connection to the MySQL database."""
        try:
            conn = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_name
            )
            return conn
        except Error as e:
            print(f"Error connecting to MySQL (get_connection): {e}")
            return None

    def create_database_if_not_exists(self):
        try:
            # Connect without database first
            conn = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            print(f"Error creating database: {e}")

    def init_database(self):
        """Creates tables if this is the first time running."""
        self.create_database_if_not_exists()
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()

        # Table: Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100),
                email VARCHAR(100),
                age INT,
                cnic VARCHAR(20), 
                username VARCHAR(50) UNIQUE,
                password VARCHAR(255),
                role VARCHAR(20) DEFAULT 'passenger'
            )
        """)

        # Table: Trains
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trains (
                train_id INT AUTO_INCREMENT PRIMARY KEY,
                number VARCHAR(20) UNIQUE,
                name VARCHAR(100),
                source VARCHAR(50),
                dest VARCHAR(50),
                date VARCHAR(20),
                time VARCHAR(20),
                seats_economy INT DEFAULT 0,
                total_seats_economy INT DEFAULT 0,
                price_economy FLOAT DEFAULT 0.0,
                seats_business INT DEFAULT 0,
                total_seats_business INT DEFAULT 0,
                price_business FLOAT DEFAULT 0.0,
                seats_first INT DEFAULT 0,
                total_seats_first INT DEFAULT 0,
                price_first FLOAT DEFAULT 0.0,
                delay INT DEFAULT 0,
                status VARCHAR(50) DEFAULT 'On Time'
            )
        """)

        # Table: Bookings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY,
                pnr VARCHAR(50) UNIQUE,
                user_id INT,
                train_id INT,
                booking_date VARCHAR(20),
                class_type VARCHAR(20),
                seat_number INT,
                status VARCHAR(50) DEFAULT 'Confirmed',
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE
            )
        """)
        
        # Create Default Admin
        cursor.execute("SELECT * FROM users WHERE username = 'Admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (full_name, username, password, role) VALUES ('System Admin', 'Admin', '12345', 'admin')")
        
        self.run_migrations(cursor)

        conn.commit()
        print("MySQL Database initialized successfully.")
        cursor.close()
        conn.close()

    def run_migrations(self, cursor):
        """Runs `ALTER TABLE` commands safely to upgrade pre-existing tables."""
        
        # Migrations for trains table
        trains_columns = [
            ("seats_economy", "INT DEFAULT 0"),
            ("total_seats_economy", "INT DEFAULT 0"),
            ("price_economy", "FLOAT DEFAULT 0.0"),
            ("seats_business", "INT DEFAULT 0"),
            ("total_seats_business", "INT DEFAULT 0"),
            ("price_business", "FLOAT DEFAULT 0.0"),
            ("seats_first", "INT DEFAULT 0"),
            ("total_seats_first", "INT DEFAULT 0"),
            ("price_first", "FLOAT DEFAULT 0.0")
        ]
        
        for col_name, col_type in trains_columns:
            try:
                cursor.execute(f"ALTER TABLE trains ADD COLUMN {col_name} {col_type}")
            except Error as e:
                # 1060 is "Duplicate column name", meaning column already exists (safe to ignore)
                if e.errno != 1060: print(f"Migration Error (trains.{col_name}): {e}")

        # Try to drop old trains columns if they exist
        for old_col in ["seats", "total_seats", "price"]:
            try:
                cursor.execute(f"ALTER TABLE trains DROP COLUMN {old_col}")
            except Error as e:
                if e.errno != 1091: print(f"Migration Drop Error (trains.{old_col}): {e}") # 1091: Can't drop; check that column/key exists

        # Migrations for bookings table
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN class_type VARCHAR(20) DEFAULT 'Economy'")
        except Error as e:
            if e.errno != 1060: print(f"Migration Error (bookings.class_type): {e}")


    # --- DATA METHODS ---

    def register_user(self, data):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            query = "INSERT INTO users (full_name, email, age, cnic, username, password, role) VALUES (%s, %s, %s, %s, %s, %s, 'passenger')"
            values = (data['name'], data['email'], data['age'], data['cnic'], data['username'], data['password'])
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as e:
            print(f"Register Error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def login_user(self, username, password, role_check):
        if role_check == 'admin' and username == 'Admin' and password == '12345':
            return {'user_id': 0, 'username': 'Admin', 'full_name': 'System Administrator', 'role': 'admin'}

        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()
            
            if user:
                if role_check and user['role'] != role_check:
                    return None
                return user
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_all_users(self):
        conn = self.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT full_name as name, username, email, role FROM users")
            return cursor.fetchall()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_train(self, data):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            journey_date = data.get('date')
            if journey_date == '':
                journey_date = None

            query = """INSERT INTO trains (
                number, name, source, dest, date, time, 
                seats_economy, total_seats_economy, price_economy,
                seats_business, total_seats_business, price_business,
                seats_first, total_seats_first, price_first,
                delay, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            values = (
                data['number'], data['name'], data['source'], data['dest'], 
                journey_date, data['time'], 
                data.get('seats_economy', 0), data.get('seats_economy', 0), data.get('price_economy', 0),
                data.get('seats_business', 0), data.get('seats_business', 0), data.get('price_business', 0),
                data.get('seats_first', 0), data.get('seats_first', 0), data.get('price_first', 0),
                data.get('delay', 0), data.get('status', 'On Time')
            )
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as e:
            print(f"Add Train Error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def edit_train(self, train_id, data):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            journey_date = data.get('date')
            if journey_date == '':
                journey_date = None

            query = """UPDATE trains SET
                number=%s, name=%s, source=%s, dest=%s, date=%s, time=%s, 
                seats_economy=%s, total_seats_economy=%s, price_economy=%s,
                seats_business=%s, total_seats_business=%s, price_business=%s,
                seats_first=%s, total_seats_first=%s, price_first=%s,
                delay=%s, status=%s
                WHERE train_id=%s"""
            
            values = (
                data['number'], data['name'], data['source'], data['dest'], 
                journey_date, data['time'], 
                data.get('seats_economy', 0), data.get('seats_economy', 0), data.get('price_economy', 0),
                data.get('seats_business', 0), data.get('seats_business', 0), data.get('price_business', 0),
                data.get('seats_first', 0), data.get('seats_first', 0), data.get('price_first', 0),
                data.get('delay', 0), data.get('status', 'On Time'),
                train_id
            )
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as e:
            print(f"Edit Train Error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_train(self, train_id):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trains WHERE train_id = %s", (train_id,))
            conn.commit()
            return True
        except Error as e:
            print(f"Delete Train Error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_all_trains(self):
        conn = self.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM trains")
            return cursor.fetchall()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def book_ticket(self, data):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(dictionary=True)
            class_type = data.get('classType', 'Economy') # Economy, Business, First
            
            # Map class_type to the respective seats column
            seats_column = "seats_economy"
            if class_type == "Business":
                seats_column = "seats_business"
            elif class_type == "First":
                seats_column = "seats_first"

            # 1. Check availability
            cursor.execute(f"SELECT {seats_column} FROM trains WHERE train_id = %s", (data['trainId'],))
            result = cursor.fetchone()
            
            if result and result[seats_column] > 0:
                cursor = conn.cursor()
                # 2. Insert Booking
                query = "INSERT INTO bookings (pnr, user_id, train_id, booking_date, class_type, seat_number) VALUES (%s, %s, %s, %s, %s, %s)"
                values = (data['pnr'], data['userId'], data['trainId'], data['date'], class_type, data['seat'])
                cursor.execute(query, values)
                
                # 3. Decrement Seat Count
                cursor.execute(f"UPDATE trains SET {seats_column} = {seats_column} - 1 WHERE train_id = %s", (data['trainId'],))
                conn.commit()
                return True
            return False
        except Error as e:
            print(f"Booking Error: {e}")
            conn.rollback()
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_user_bookings(self, user_id):
        conn = self.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT b.pnr, b.booking_date, b.class_type, b.seat_number, t.name as train_name, t.number as train_number, t.source, t.dest 
                FROM bookings b
                JOIN trains t ON b.train_id = t.train_id
                WHERE b.user_id = %s
                ORDER BY b.booking_id DESC
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_booking_by_pnr(self, pnr):
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT b.pnr, b.status, b.class_type, b.seat_number, t.name as train_name, t.number as train_number 
                FROM bookings b
                JOIN trains t ON b.train_id = t.train_id
                WHERE b.pnr = %s
            """
            cursor.execute(query, (pnr,))
            return cursor.fetchone()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_train_bookings(self, train_id):
        conn = self.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT u.full_name as user_name, u.cnic, b.pnr, b.class_type, b.seat_number, b.status
                FROM bookings b
                JOIN users u ON b.user_id = u.user_id
                WHERE b.train_id = %s
                ORDER BY b.seat_number ASC
            """
            cursor.execute(query, (train_id,))
            return cursor.fetchall()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()



# import oracledb

# class RailwayBackend:
#     def __init__(self):
#         # --- ORACLE CONFIGURATION ---
#         self.db_config = {
#             'user': 'system',          # <--- Put your Oracle username here
#             'password': 'password2', # <--- Put your Oracle password here
#             'dsn': 'localhost:1521/xe'  # <--- Change 'xe' to 'orcl' if you are using Oracle Enterprise
#         }
#         self.init_database()

#     def get_connection(self):
#         """Creates a new database connection."""
#         try:
#             conn = oracledb.connect(**self.db_config)
#             return conn
#         except oracledb.Error as e:
#             print(f"Error connecting to Oracle: {e}")
#             return None

#     def _execute_ddl(self, cursor, query):
#         """Helper to ignore 'name is already used' errors in Oracle"""
#         try:
#             cursor.execute(query)
#         except oracledb.DatabaseError as e:
#             error_obj, = e.args
#             if error_obj.code == 955:  # ORA-00955: name is already used
#                 pass
#             else:
#                 print(f"DDL Error: {e}")

#     def init_database(self):
#         """Creates the tables if they don't exist."""
#         conn = self.get_connection()
#         if not conn: return
        
#         cursor = conn.cursor()

#         # Table: Users (Oracle uses NUMBER GENERATED ALWAYS AS IDENTITY instead of AUTO_INCREMENT)
#         self._execute_ddl(cursor, """
#             CREATE TABLE users (
#                 user_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
#                 full_name VARCHAR2(100),
#                 email VARCHAR2(100),
#                 age NUMBER,
#                 cnic VARCHAR2(20), 
#                 username VARCHAR2(50) UNIQUE,
#                 password VARCHAR2(255),
#                 role VARCHAR2(10) DEFAULT 'passenger'
#             )
#         """)

#         # Table: Trains (Renamed 'date', 'time', 'number' to avoid Oracle reserved word issues)
#         self._execute_ddl(cursor, """
#             CREATE TABLE trains (
#                 train_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
#                 train_no VARCHAR2(20) UNIQUE,
#                 name VARCHAR2(100),
#                 source VARCHAR2(50),
#                 dest VARCHAR2(50),
#                 journey_date DATE,
#                 dep_time VARCHAR2(20),
#                 seats NUMBER,
#                 total_seats NUMBER,
#                 price NUMBER DEFAULT 0,
#                 delay NUMBER DEFAULT 0,
#                 status VARCHAR2(20) DEFAULT 'On Time'
#             )
#         """)

#         # Table: Bookings
#         self._execute_ddl(cursor, """
#             CREATE TABLE bookings (
#                 booking_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
#                 pnr VARCHAR2(20) UNIQUE,
#                 user_id NUMBER,
#                 train_id NUMBER,
#                 booking_date DATE,
#                 seat_number NUMBER,
#                 status VARCHAR2(20) DEFAULT 'Confirmed',
#                 CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id),
#                 CONSTRAINT fk_train FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE
#             )
#         """)
        
#         # Create Default Admin
#         cursor.execute("SELECT * FROM users WHERE username = 'Admin'")
#         if not cursor.fetchone():
#             cursor.execute("INSERT INTO users (full_name, username, password, role) VALUES ('System Admin', 'Admin', '12345', 'admin')")
        
#         conn.commit()
#         print("Oracle Database initialized successfully.")
#         cursor.close()
#         conn.close()

#     # --- HELPER METHOD FOR DICTIONARIES ---
#     def _fetch_dicts(self, cursor):
#         """Converts Oracle cursor results into a list of dictionaries"""
#         columns = [col[0].lower() for col in cursor.description]
#         return [dict(zip(columns, row)) for row in cursor.fetchall()]

#     # --- DATA METHODS ---

#     def register_user(self, data):
#         conn = self.get_connection()
#         if not conn: return False
#         try:
#             cursor = conn.cursor()
#             # Oracle uses :1, :2 for bind variables instead of %s
#             query = "INSERT INTO users (full_name, email, age, cnic, username, password, role) VALUES (:1, :2, :3, :4, :5, :6, 'passenger')"
#             values = (data['name'], data['email'], data['age'], data['cnic'], data['username'], data['password'])
#             cursor.execute(query, values)
#             conn.commit()
#             return True
#         except oracledb.Error as e:
#             print(f"Register Error: {e}")
#             return False
#         finally:
#             conn.close()

#     def login_user(self, username, password, role_check):
#         if role_check == 'admin' and username == 'Admin' and password == '12345':
#             return {'user_id': 0, 'username': 'Admin', 'full_name': 'System Administrator', 'role': 'admin'}

#         conn = self.get_connection()
#         if not conn: return None
#         try:
#             cursor = conn.cursor()
#             query = "SELECT user_id, full_name, username, role FROM users WHERE username = :1 AND password = :2"
#             cursor.execute(query, (username, password))
            
#             result = self._fetch_dicts(cursor)
#             if result:
#                 user = result[0]
#                 if role_check and user['role'] != role_check:
#                     return None
#                 return user
#             return None
#         finally:
#             conn.close()

#     def get_all_users(self):
#         conn = self.get_connection()
#         if not conn: return []
#         try:
#             cursor = conn.cursor()
#             cursor.execute("SELECT full_name as name, username, email, role FROM users")
#             return self._fetch_dicts(cursor)
#         finally:
#             conn.close()

#     def add_train(self, data):
#         conn = self.get_connection()
#         if not conn: return False
#         try:
#             cursor = conn.cursor()
#             journey_date = data.get('date')
#             if journey_date == '':
#                 journey_date = None

#             query = """INSERT INTO trains (train_no, name, source, dest, journey_date, dep_time, seats, total_seats, price, delay, status) 
#                        VALUES (:1, :2, :3, :4, TO_DATE(:5, 'YYYY-MM-DD'), :6, :7, :8, :9, :10, :11)"""
            
#             values = (
#                 data['number'], 
#                 data['name'], 
#                 data['source'], 
#                 data['dest'], 
#                 journey_date, 
#                 data['time'], 
#                 data['seats'], 
#                 data['seats'], 
#                 data.get('price', 0), 
#                 data.get('delay', 0), 
#                 data.get('status', 'On Time')
#             )
#             cursor.execute(query, values)
#             conn.commit()
#             return True
#         except oracledb.Error as e:
#             print(f"Add Train Error: {e}")
#             return False
#         finally:
#             conn.close()

#     def delete_train(self, train_id):
#         conn = self.get_connection()
#         if not conn: return False
#         try:
#             cursor = conn.cursor()
#             query = "DELETE FROM trains WHERE train_id = :1"
#             cursor.execute(query, (train_id,))
#             conn.commit()
#             return True
#         except oracledb.Error as e:
#             print(f"Delete Train Error: {e}")
#             return False
#         finally:
#             conn.close()

#     def get_all_trains(self):
#         conn = self.get_connection()
#         if not conn: return []
#         try:
#             cursor = conn.cursor()
#             # Alias columns back to what the frontend expects
#             query = """SELECT train_id, train_no as "number", name, source, dest, 
#                               TO_CHAR(journey_date, 'YYYY-MM-DD') as "date", 
#                               dep_time as "time", seats, total_seats, price, delay, status 
#                        FROM trains"""
#             cursor.execute(query)
#             return self._fetch_dicts(cursor)
#         finally:
#             conn.close()

#     def book_ticket(self, data):
#         conn = self.get_connection()
#         if not conn: return False
#         try:
#             cursor = conn.cursor()
#             cursor.execute("SELECT seats FROM trains WHERE train_id = :1 FOR UPDATE", (data['trainId'],))
#             result = cursor.fetchone()
            
#             if result and result[0] > 0:
#                 query = "INSERT INTO bookings (pnr, user_id, train_id, booking_date, seat_number) VALUES (:1, :2, :3, TO_DATE(:4, 'YYYY-MM-DD'), :5)"
#                 values = (data['pnr'], data['userId'], data['trainId'], data['date'], data['seat'])
#                 cursor.execute(query, values)
                
#                 cursor.execute("UPDATE trains SET seats = seats - 1 WHERE train_id = :1", (data['trainId'],))
#                 conn.commit()
#                 return True
            
#             conn.rollback()
#             return False
#         except oracledb.Error as e:
#             print(f"Booking Error: {e}")
#             conn.rollback()
#             return False
#         finally:
#             conn.close()

#     def get_user_bookings(self, user_id):
#         conn = self.get_connection()
#         if not conn: return []
#         try:
#             cursor = conn.cursor()
#             query = """
#                 SELECT b.pnr, TO_CHAR(b.booking_date, 'YYYY-MM-DD') as booking_date, b.seat_number, 
#                        t.name as train_name, t.train_no as train_number, t.source, t.dest 
#                 FROM bookings b
#                 JOIN trains t ON b.train_id = t.train_id
#                 WHERE b.user_id = :1
#                 ORDER BY b.booking_id DESC
#             """
#             cursor.execute(query, (user_id,))
#             return self._fetch_dicts(cursor)
#         finally:
#             conn.close()

#     def get_booking_by_pnr(self, pnr):
#         conn = self.get_connection()
#         if not conn: return None
#         try:
#             cursor = conn.cursor()
#             query = """
#                 SELECT b.pnr, b.status, b.seat_number, t.name as train_name, t.train_no as train_number 
#                 FROM bookings b
#                 JOIN trains t ON b.train_id = t.train_id
#                 WHERE b.pnr = :1
#             """
#             cursor.execute(query, (pnr,))
#             result = self._fetch_dicts(cursor)
#             return result[0] if result else None
#         finally:
#             conn.close()




            