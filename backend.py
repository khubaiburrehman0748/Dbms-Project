import sqlite3

class RailwayBackend:
    def __init__(self):
        # Creates a local file named 'railway.db' in your folder. No passwords needed!
        self.db_name = 'railway.db'
        self.init_database()

    def get_connection(self):
        """Creates a connection to the local SQLite file."""
        # check_same_thread=False is needed so Flask doesn't complain
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        # This magically makes the database return dictionaries instead of raw tuples!
        conn.row_factory = sqlite3.Row 
        return conn

    def init_database(self):
        """Creates tables if this is the first time running."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Table: Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT,
                age INTEGER,
                cnic TEXT, 
                username TEXT UNIQUE,
                password TEXT,
                role TEXT DEFAULT 'passenger'
            )
        """)

        # Table: Trains
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trains (
                train_id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE,
                name TEXT,
                source TEXT,
                dest TEXT,
                date TEXT,
                time TEXT,
                seats INTEGER,
                total_seats INTEGER,
                price REAL DEFAULT 0.0,
                delay INTEGER DEFAULT 0,
                status TEXT DEFAULT 'On Time'
            )
        """)

        # Table: Bookings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pnr TEXT UNIQUE,
                user_id INTEGER,
                train_id INTEGER,
                booking_date TEXT,
                seat_number INTEGER,
                status TEXT DEFAULT 'Confirmed',
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE
            )
        """)
        
        # Create Default Admin
        cursor.execute("SELECT * FROM users WHERE username = 'Admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (full_name, username, password, role) VALUES ('System Admin', 'Admin', '12345', 'admin')")
        
        conn.commit()
        print("SQLite Database initialized successfully. Zero configuration needed!")
        conn.close()

    # --- DATA METHODS ---

    def register_user(self, data):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # SQLite uses ? instead of %s or :1
            query = "INSERT INTO users (full_name, email, age, cnic, username, password, role) VALUES (?, ?, ?, ?, ?, ?, 'passenger')"
            values = (data['name'], data['email'], data['age'], data['cnic'], data['username'], data['password'])
            cursor.execute(query, values)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Register Error: {e}")
            return False
        finally:
            conn.close()

    def login_user(self, username, password, role_check):
        if role_check == 'admin' and username == 'Admin' and password == '12345':
            return {'user_id': 0, 'username': 'Admin', 'full_name': 'System Administrator', 'role': 'admin'}

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM users WHERE username = ? AND password = ?"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()
            
            if user:
                user_dict = dict(user) # Convert to dictionary
                if role_check and user_dict['role'] != role_check:
                    return None
                return user_dict
            return None
        finally:
            conn.close()

    def get_all_users(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT full_name as name, username, email, role FROM users")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def add_train(self, data):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            journey_date = data.get('date')
            if journey_date == '':
                journey_date = None

            query = "INSERT INTO trains (number, name, source, dest, date, time, seats, total_seats, price, delay, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            values = (
                data['number'], data['name'], data['source'], data['dest'], 
                journey_date, data['time'], data['seats'], data['seats'], 
                data.get('price', 0), data.get('delay', 0), data.get('status', 'On Time')
            )
            cursor.execute(query, values)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add Train Error: {e}")
            return False
        finally:
            conn.close()

    def delete_train(self, train_id):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trains WHERE train_id = ?", (train_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Delete Train Error: {e}")
            return False
        finally:
            conn.close()

    def get_all_trains(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trains")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def book_ticket(self, data):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # 1. Check availability
            cursor.execute("SELECT seats FROM trains WHERE train_id = ?", (data['trainId'],))
            result = cursor.fetchone()
            
            if result and result['seats'] > 0:
                # 2. Insert Booking
                query = "INSERT INTO bookings (pnr, user_id, train_id, booking_date, seat_number) VALUES (?, ?, ?, ?, ?)"
                values = (data['pnr'], data['userId'], data['trainId'], data['date'], data['seat'])
                cursor.execute(query, values)
                
                # 3. Decrement Seat Count
                cursor.execute("UPDATE trains SET seats = seats - 1 WHERE train_id = ?", (data['trainId'],))
                conn.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Booking Error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_user_bookings(self, user_id):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT b.pnr, b.booking_date, b.seat_number, t.name as train_name, t.number as train_number, t.source, t.dest 
                FROM bookings b
                JOIN trains t ON b.train_id = t.train_id
                WHERE b.user_id = ?
                ORDER BY b.booking_id DESC
            """
            cursor.execute(query, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_booking_by_pnr(self, pnr):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT b.pnr, b.status, b.seat_number, t.name as train_name, t.number as train_number 
                FROM bookings b
                JOIN trains t ON b.train_id = t.train_id
                WHERE b.pnr = ?
            """
            cursor.execute(query, (pnr,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
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




            