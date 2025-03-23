import sqlite3
import threading
from datetime import datetime, timedelta

class HospitalDB:
    def __init__(self, db_name="hospital.db"):
        """Initialize the database connection storage"""
        self.db_name = db_name
        # Use thread-local storage to store connections
        self.local = threading.local()
        # Create initial connection in the current thread
        self.connect()
        self.create_tables()

    def connect(self):
        """Connect to the SQLite database in the current thread"""
        try:
            # Create a new connection for the current thread
            self.local.conn = sqlite3.connect(self.db_name)
            self.local.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.local.cursor = self.local.conn.cursor()
            print(f"Connected to database: {self.db_name}")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def close(self):
        """Close the database connection for the current thread"""
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            print("Database connection closed")

    def ensure_connection(self):
        """Ensure that the current thread has a valid connection"""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.connect()
        return self.local.conn, self.local.cursor

    def create_tables(self):
        """Create all necessary tables if they don't exist"""
        try:
            conn, cursor = self.ensure_connection()
            
            # Users table (doctors, nurses, staff)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    specialization TEXT,
                    phone TEXT,
                    address TEXT,
                    date_joined TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # Patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    date_of_birth TEXT,
                    gender TEXT,
                    blood_group TEXT,
                    registration_date TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # Medical records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medical_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    diagnosis TEXT,
                    treatment TEXT,
                    notes TEXT,
                    record_date TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients (id),
                    FOREIGN KEY (doctor_id) REFERENCES users (id)
                )
            ''')

            # Appointments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'scheduled',
                    FOREIGN KEY (patient_id) REFERENCES patients (id),
                    FOREIGN KEY (doctor_id) REFERENCES users (id)
                )
            ''')

            # Prescriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prescriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    medication TEXT NOT NULL,
                    dosage TEXT,
                    frequency TEXT,
                    duration TEXT,
                    notes TEXT,
                    FOREIGN KEY (record_id) REFERENCES medical_records (id)
                )
            ''')

            # Billing table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS billing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    record_id INTEGER,
                    amount REAL NOT NULL,
                    payment_status TEXT DEFAULT 'pending',
                    payment_date TEXT,
                    payment_method TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients (id),
                    FOREIGN KEY (record_id) REFERENCES medical_records (id)
                )
            ''')

            conn.commit()
            print("Tables created successfully")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

    # User management functions
    def add_user(self, name, email, password, role, specialization=None, phone=None, address=None):
        """Add a new user (doctor, nurse, staff) to the database"""
        try:
            conn, cursor = self.ensure_connection()
            date_joined = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO users (name, email, password, role, specialization, phone, address, date_joined)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, password, role, specialization, phone, address, date_joined))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return None

    def get_user(self, user_id=None, email=None):
        """Get user details by ID or email"""
        try:
            conn, cursor = self.ensure_connection()
            if user_id:
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            elif email:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            else:
                return None
            result = cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            print(f"Error getting user: {e}")
            return None

    def get_all_users(self, role=None):
        """Get all users or filter by role"""
        try:
            conn, cursor = self.ensure_connection()
            if role:
                cursor.execute("SELECT * FROM users WHERE role = ?", (role,))
            else:
                cursor.execute("SELECT * FROM users")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting users: {e}")
            return []

    def update_user(self, user_id, **kwargs):
        """Update user details"""
        try:
            conn, cursor = self.ensure_connection()
            valid_fields = ["name", "email", "password", "role", "specialization", "phone", "address", "status"]
            updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
            
            if not updates:
                return False

            set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
            values = list(updates.values())
            values.append(user_id)

            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id):
        """Delete a user (or set status to inactive)"""
        try:
            conn, cursor = self.ensure_connection()
            # Soft delete by setting status to 'inactive'
            cursor.execute("UPDATE users SET status = 'inactive' WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False

    # Patient management functions
    def add_patient(self, name, email=None, phone=None, address=None, date_of_birth=None, gender=None, blood_group=None):
        """Add a new patient to the database"""
        try:
            conn, cursor = self.ensure_connection()
            registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO patients (name, email, phone, address, date_of_birth, gender, blood_group, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, address, date_of_birth, gender, blood_group, registration_date))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding patient: {e}")
            return None

    def get_patient(self, patient_id):
        """Get patient details by ID"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            print(f"Error getting patient: {e}")
            return None

    def get_all_patients(self):
        """Get all patients"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute("SELECT * FROM patients WHERE status = 'active'")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting patients: {e}")
            return []

    def search_patients(self, query):
        """Search patients by name, email, or phone"""
        try:
            conn, cursor = self.ensure_connection()
            search_term = f"%{query}%"
            cursor.execute('''
                SELECT * FROM patients 
                WHERE (name LIKE ? OR email LIKE ? OR phone LIKE ?) 
                AND status = 'active'
            ''', (search_term, search_term, search_term))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching patients: {e}")
            return []

    def update_patient(self, patient_id, **kwargs):
        """Update patient details"""
        try:
            conn, cursor = self.ensure_connection()
            valid_fields = ["name", "email", "phone", "address", "date_of_birth", "gender", "blood_group", "status"]
            updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
            
            if not updates:
                return False

            set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
            values = list(updates.values())
            values.append(patient_id)

            cursor.execute(f"UPDATE patients SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating patient: {e}")
            return False

    def delete_patient(self, patient_id):
        """Delete a patient (or set status to inactive)"""
        try:
            conn, cursor = self.ensure_connection()
            # Soft delete by setting status to 'inactive'
            cursor.execute("UPDATE patients SET status = 'inactive' WHERE id = ?", (patient_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting patient: {e}")
            return False

    # Medical record functions
    def add_medical_record(self, patient_id, doctor_id, diagnosis, treatment, notes=None):
        """Add a new medical record"""
        try:
            conn, cursor = self.ensure_connection()
            record_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO medical_records (patient_id, doctor_id, diagnosis, treatment, notes, record_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (patient_id, doctor_id, diagnosis, treatment, notes, record_date))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding medical record: {e}")
            return None

    def get_patient_records(self, patient_id):
        """Get all medical records for a patient"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                SELECT mr.*, u.name as doctor_name 
                FROM medical_records mr
                JOIN users u ON mr.doctor_id = u.id
                WHERE mr.patient_id = ?
                ORDER BY mr.record_date DESC
            ''', (patient_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting patient records: {e}")
            return []

    def get_doctor_records(self, doctor_id):
        """Get all medical records created by a doctor"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                SELECT mr.*, p.name as patient_name 
                FROM medical_records mr
                JOIN patients p ON mr.patient_id = p.id
                WHERE mr.doctor_id = ?
                ORDER BY mr.record_date DESC
            ''', (doctor_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting doctor records: {e}")
            return []

    # Appointment functions
    def add_appointment(self, patient_id, doctor_id, appointment_date, appointment_time, reason=None):
        """Add a new appointment"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (patient_id, doctor_id, appointment_date, appointment_time, reason))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding appointment: {e}")
            return None

    def get_appointments(self, patient_id=None, doctor_id=None, date=None):
        """Get appointments, optionally filtered by patient, doctor, or date"""
        try:
            conn, cursor = self.ensure_connection()
            query = "SELECT a.*, p.name as patient_name, u.name as doctor_name FROM appointments a"
            query += " JOIN patients p ON a.patient_id = p.id"
            query += " JOIN users u ON a.doctor_id = u.id WHERE 1=1"
            params = []

            if patient_id:
                query += " AND a.patient_id = ?"
                params.append(patient_id)
            if doctor_id:
                query += " AND a.doctor_id = ?"
                params.append(doctor_id)
            if date:
                query += " AND a.appointment_date = ?"
                params.append(date)

            query += " ORDER BY a.appointment_date, a.appointment_time"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting appointments: {e}")
            return []

    def update_appointment_status(self, appointment_id, status):
        """Update the status of an appointment"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute(
                "UPDATE appointments SET status = ? WHERE id = ?", 
                (status, appointment_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating appointment status: {e}")
            return False

    # Prescription functions
    def add_prescription(self, record_id, medication, dosage=None, frequency=None, duration=None, notes=None):
        """Add a prescription to a medical record"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                INSERT INTO prescriptions (record_id, medication, dosage, frequency, duration, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (record_id, medication, dosage, frequency, duration, notes))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding prescription: {e}")
            return None

    def get_prescriptions(self, record_id):
        """Get all prescriptions for a medical record"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute("SELECT * FROM prescriptions WHERE record_id = ?", (record_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting prescriptions: {e}")
            return []

    def get_patient_prescriptions(self, patient_id):
        """Get all prescriptions for a patient across all medical records"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                SELECT p.*, mr.diagnosis, mr.record_date
                FROM prescriptions p
                JOIN medical_records mr ON p.record_id = mr.id
                WHERE mr.patient_id = ?
                ORDER BY mr.record_date DESC
            ''', (patient_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting patient prescriptions: {e}")
            return []

    # Billing functions
    def add_bill(self, patient_id, amount, record_id=None):
        """Add a new bill for a patient"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                INSERT INTO billing (patient_id, record_id, amount)
                VALUES (?, ?, ?)
            ''', (patient_id, record_id, amount))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding bill: {e}")
            return None

    def update_payment(self, bill_id, payment_status, payment_method=None):
        """Update payment status and method for a bill"""
        try:
            conn, cursor = self.ensure_connection()
            payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if payment_status == 'paid' else None
            cursor.execute('''
                UPDATE billing 
                SET payment_status = ?, payment_method = ?, payment_date = ?
                WHERE id = ?
            ''', (payment_status, payment_method, payment_date, bill_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating payment: {e}")
            return False

    def get_patient_bills(self, patient_id):
        """Get all bills for a patient"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                SELECT b.*, p.name as patient_name
                FROM billing b
                JOIN patients p ON b.patient_id = p.id
                WHERE b.patient_id = ?
                ORDER BY b.payment_date DESC
            ''', (patient_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting patient bills: {e}")
            return []

    def get_pending_bills(self):
        """Get all pending bills"""
        try:
            conn, cursor = self.ensure_connection()
            cursor.execute('''
                SELECT b.*, p.name as patient_name
                FROM billing b
                JOIN patients p ON b.patient_id = p.id
                WHERE b.payment_status = 'pending'
                ORDER BY b.id DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting pending bills: {e}")
            return []

    # Dashboard statistics
    def get_dashboard_stats(self):
        """Get statistics for the dashboard"""
        try:
            conn, cursor = self.ensure_connection()
            stats = {}
            
            # Total patients
            cursor.execute("SELECT COUNT(*) as count FROM patients WHERE status = 'active'")
            result = cursor.fetchone()
            stats["total_patients"] = result["count"] if result else 0
            
            # New patients in the last 30 days
            cursor.execute('''
                SELECT COUNT(*) as count FROM patients 
                WHERE status = 'active' AND registration_date >= datetime('now', '-1 days')
            ''')
            result = cursor.fetchone()
            stats["new_patients"] = result["count"] if result else 0
            
            # Total appointments
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            result = cursor.fetchone()
            stats["total_appointments"] = result["count"] if result else 0
            
            # New appointments in the next 7 days
            cursor.execute('''
                SELECT COUNT(*) as count FROM appointments 
                WHERE appointment_date >= date('now') AND appointment_date <= date('now', '+7 days')
            ''')
            result = cursor.fetchone()
            stats["new_appointments"] = result["count"] if result else 0
            
            # Total medical records (operations)
            cursor.execute("SELECT COUNT(*) as count FROM medical_records")
            result = cursor.fetchone()
            stats["total_operations"] = result["count"] if result else 0
            
            # New medical records in the last 30 days
            cursor.execute('''
                SELECT COUNT(*) as count FROM medical_records 
                WHERE record_date >= datetime('now', '-1 days')
            ''')
            result = cursor.fetchone()
            stats["new_operations"] = result["count"] if result else 0
            
            # Calculate average wait time (placeholder - this would need actual wait time data)
            stats["avg_wait_time"] = "15 min"
            
            return stats
        except sqlite3.Error as e:
            print(f"Error getting dashboard stats: {e}")
            return {
                "total_patients": 0,
                "new_patients": 0,
                "total_appointments": 0,
                "new_appointments": 0,
                "total_operations": 0,
                "new_operations": 0,
                "avg_wait_time": "0 min"
            }

    # Get department performance data
    def get_department_performance(self):
        """Get department performance data for the dashboard"""
        # This would typically come from calculated metrics in a real system
        # For now, we'll return sample data
        return [
            {"department": "Cardiology", "efficiency": 85},
            {"department": "Neurology", "efficiency": 78},
            {"department": "Pediatrics", "efficiency": 92},
            {"department": "Orthopedics", "efficiency": 73},
            {"department": "Oncology", "efficiency": 80}
        ]
    
    # Get recent activity data
    def get_recent_activity(self, limit=5):
        """Get recent activity data for the dashboard"""
        try:
            conn, cursor = self.ensure_connection()
            activities = []
            
            # Get latest patients
            cursor.execute('''
                SELECT 'new_patient' as type, 
                       'New patient admitted' as title, 
                       name as description, 
                       registration_date as timestamp 
                FROM patients 
                ORDER BY registration_date DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest appointments
            cursor.execute('''
                SELECT 'appointment' as type, 
                       'Appointment scheduled' as title, 
                       p.name || ' with ' || u.name as description, 
                       a.appointment_date || ' ' || a.appointment_time as timestamp 
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN users u ON a.doctor_id = u.id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest medical records
            cursor.execute('''
                SELECT 'medical_record' as type, 
                       diagnosis as title, 
                       p.name || ' by ' || u.name as description, 
                       record_date as timestamp 
                FROM medical_records mr
                JOIN patients p ON mr.patient_id = p.id
                JOIN users u ON mr.doctor_id = u.id
                ORDER BY record_date DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Sort activities by timestamp
            activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return activities[:limit]
        except sqlite3.Error as e:
            print(f"Error getting recent activity: {e}")
            return []
    
    # Get today's appointments
    def get_todays_appointments(self, doctor_id=None):
        """Get today's appointments for the dashboard"""
        try:
            conn, cursor = self.ensure_connection()
            today = datetime.now().strftime("%Y-%m-%d")
            query = '''
                SELECT a.id, p.name as patient_name, u.name as doctor_name, 
                       a.appointment_time, a.reason, a.status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN users u ON a.doctor_id = u.id
                WHERE a.appointment_date = ?
            '''
            params = [today]
            
            if doctor_id:
                query += " AND a.doctor_id = ?"
                params.append(doctor_id)
                
            query += " ORDER BY a.appointment_time"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting today's appointments: {e}")
            return []
    
    def get_department_chart_data(self):
        """
        Get department-based chart data for doctors
        Returns counts of doctors and patients by department (specialization)
        """
        try:
            conn, cursor = self.ensure_connection()
            # Get all departments and doctor counts
            cursor.execute('''
                SELECT specialization as department, COUNT(*) as doctor_count
                FROM users 
                WHERE role = 'doctor' AND status = 'active' AND specialization IS NOT NULL
                GROUP BY specialization
                ORDER BY doctor_count DESC
            ''')
            departments = [dict(row) for row in cursor.fetchall()]
            
            # For each department, get patient count (from medical records)
            for dept in departments:
                cursor.execute('''
                    SELECT COUNT(DISTINCT mr.patient_id) as patient_count
                    FROM medical_records mr
                    JOIN users u ON mr.doctor_id = u.id
                    WHERE u.specialization = ?
                ''', (dept['department'],))
                result = cursor.fetchone()
                dept['patient_count'] = result['patient_count'] if result else 0
                
                # Get appointment count for each department
                cursor.execute('''
                    SELECT COUNT(*) as appointment_count
                    FROM appointments a
                    JOIN users u ON a.doctor_id = u.id
                    WHERE u.specialization = ?
                ''', (dept['department'],))
                result = cursor.fetchone()
                dept['appointment_count'] = result['appointment_count'] if result else 0
                
                # Calculate average billing amount per department
                cursor.execute('''
                    SELECT AVG(b.amount) as avg_billing
                    FROM billing b
                    JOIN medical_records mr ON b.record_id = mr.id
                    JOIN users u ON mr.doctor_id = u.id
                    WHERE u.specialization = ?
                ''', (dept['department'],))
                result = cursor.fetchone()
                dept['avg_billing'] = round(result['avg_billing'], 2) if result and result['avg_billing'] else 0
            
            return departments
        except sqlite3.Error as e:
            print(f"Error getting department chart data: {e}")
            return []

    def get_department_performance_metrics(self):
        """
        Get comprehensive department performance metrics for charting
        """
        try:
            conn, cursor = self.ensure_connection()
            departments = self.get_department_chart_data()
            
            # Add more metrics
            for dept in departments:
                # Calculate appointment completion rate
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(*) as total
                    FROM appointments a
                    JOIN users u ON a.doctor_id = u.id
                    WHERE u.specialization = ?
                ''', (dept['department'],))
                result = cursor.fetchone()
                if result and result['total'] > 0:
                    dept['completion_rate'] = round((result['completed'] / result['total']) * 100, 1)
                else:
                    dept['completion_rate'] = 0
                
                # Get recent patient feedback score (placeholder - would need a separate table)
                # For this example, we'll use random scores
                import random
                dept['satisfaction_score'] = round(random.uniform(3.5, 5.0), 1)
                
                # Calculate average appointments per doctor
                if dept['doctor_count'] > 0:
                    dept['appointments_per_doctor'] = round(dept['appointment_count'] / dept['doctor_count'], 1)
                else:
                    dept['appointments_per_doctor'] = 0
                
                # Calculate average patients per doctor
                if dept['doctor_count'] > 0:
                    dept['patients_per_doctor'] = round(dept['patient_count'] / dept['doctor_count'], 1)
                else:
                    dept['patients_per_doctor'] = 0
            
            return departments
        except sqlite3.Error as e:
            print(f"Error getting department performance metrics: {e}")
            return []
    
    def get_recent_activity(self, limit=5):
        """
        Get recent activity data across the hospital system.
        
        Args:
            limit (int): Number of recent activities to return (default: 5)
        
        Returns:
            list: Recent activities with type, title, description and timestamp
        """
        try:
            conn, cursor = self.ensure_connection()
            activities = []
            
            # Get latest patients
            cursor.execute('''
                SELECT 'new_patient' as activity_type, 
                    'New patient registered' as title, 
                    name as description, 
                    registration_date as timestamp,
                    id as entity_id
                FROM patients 
                ORDER BY registration_date DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest appointments
            cursor.execute('''
                SELECT 'appointment' as activity_type, 
                    'Appointment scheduled' as title, 
                    p.name || ' with Dr. ' || u.name as description, 
                    a.appointment_date || ' ' || a.appointment_time as timestamp,
                    a.id as entity_id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN users u ON a.doctor_id = u.id
                ORDER BY a.appointment_date DESC, a.appointment_time DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest medical records
            cursor.execute('''
                SELECT 'medical_record' as activity_type, 
                    coalesce(diagnosis, 'Medical record created') as title, 
                    'Patient: ' || p.name || ' | Doctor: ' || u.name as description, 
                    record_date as timestamp,
                    mr.id as entity_id
                FROM medical_records mr
                JOIN patients p ON mr.patient_id = p.id
                JOIN users u ON mr.doctor_id = u.id
                ORDER BY record_date DESC 
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest billing records
            cursor.execute('''
                SELECT 'billing' as activity_type,
                    'Payment ' || payment_status as title,
                    'Patient: ' || p.name || ' | Amount: $' || amount as description,
                    COALESCE(payment_date, DATETIME('now')) as timestamp,
                    b.id as entity_id
                FROM billing b
                JOIN patients p ON b.patient_id = p.id
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Get latest prescription data
            cursor.execute('''
                SELECT 'prescription' as activity_type,
                    'Prescription added' as title,
                    medication || ' for patient ' || p.name as description,
                    mr.record_date as timestamp,
                    pr.id as entity_id
                FROM prescriptions pr
                JOIN medical_records mr ON pr.record_id = mr.id
                JOIN patients p ON mr.patient_id = p.id
                ORDER BY mr.record_date DESC
                LIMIT ?
            ''', (limit,))
            activities.extend([dict(row) for row in cursor.fetchall()])
            
            # Sort all activities by timestamp (newest first)
            activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Return only the requested number of activities
            return activities[:limit]
        except sqlite3.Error as e:
            print(f"Error getting recent activity: {e}")
            return []
        
    def get_todays_top_appointments(self, limit=5):
        """
        Get today's top appointments ordered by time in a simplified format.
        
        Args:
            limit (int): Maximum number of appointments to return (default: 5)
        
        Returns:
            list: Today's appointments with basic details
        """
        try:
            conn, cursor = self.ensure_connection()
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute('''
                SELECT 
                    a.id,
                    p.name as patient_name,
                    u.name as doctor_name,
                    a.appointment_time,
                    a.reason,
                    a.status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN users u ON a.doctor_id = u.id
                WHERE a.appointment_date = ?
                ORDER BY a.appointment_time ASC
                LIMIT ?
            ''', (today, limit))
            
            appointments = [dict(row) for row in cursor.fetchall()]
            return appointments
        except sqlite3.Error as e:
            print(f"Error getting today's top appointments: {e}")
            return []