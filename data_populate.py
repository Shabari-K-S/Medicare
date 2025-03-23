import sqlite3
import hashlib
import datetime
import random
from datetime import timedelta

class DatabasePopulator:
    def __init__(self, db_path="hospital.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def populate_database(self):
        
        # Populate users (doctors, nurses, admin staff)
        users_data = [
            {'name': 'Dr. John Smith', 'email': 'john.smith@hospital.com', 'password': 'password123', 'role': 'doctor', 'specialization': 'Cardiology', 'phone': '555-123-4567', 'address': '123 Medical Lane', 'date_joined': '2022-01-15'},
            {'name': 'Dr. Sarah Johnson', 'email': 'sarah.johnson@hospital.com', 'password': 'doctor456', 'role': 'doctor', 'specialization': 'Neurology', 'phone': '555-234-5678', 'address': '456 Health Street', 'date_joined': '2021-11-20'},
            {'name': 'Dr. Michael Wong', 'email': 'michael.wong@hospital.com', 'password': 'secure789', 'role': 'doctor', 'specialization': 'Pediatrics', 'phone': '555-345-6789', 'address': '789 Wellness Ave', 'date_joined': '2023-02-10'},
            {'name': 'Nurse Emily Davis', 'email': 'emily.davis@hospital.com', 'password': 'nurse123', 'role': 'nurse', 'specialization': 'Emergency', 'phone': '555-456-7890', 'address': '234 Care Road', 'date_joined': '2022-08-05'},
            {'name': 'Nurse Robert Chen', 'email': 'robert.chen@hospital.com', 'password': 'chen456', 'role': 'nurse', 'specialization': 'Pediatrics', 'phone': '555-567-8901', 'address': '567 Mercy Drive', 'date_joined': '2023-03-15'},
            {'name': 'Dr. Lisa Patel', 'email': 'lisa.patel@hospital.com', 'password': 'patel789', 'role': 'doctor', 'specialization': 'Dermatology', 'phone': '555-678-9012', 'address': '890 Healing Court', 'date_joined': '2022-05-25'},
            {'name': 'Admin Jessica Brown', 'email': 'jessica.brown@hospital.com', 'password': 'admin123', 'role': 'admin', 'specialization': None, 'phone': '555-789-0123', 'address': '345 Admin Street', 'date_joined': '2021-09-30'},
            {'name': 'Dr. Thomas Wilson', 'email': 'thomas.wilson@hospital.com', 'password': 'wilson456', 'role': 'doctor', 'specialization': 'Orthopedics', 'phone': '555-890-1234', 'address': '678 Doctor Blvd', 'date_joined': '2023-01-10'},
            {'name': 'Nurse Maria Garcia', 'email': 'maria.garcia@hospital.com', 'password': 'garcia789', 'role': 'nurse', 'specialization': 'Surgery', 'phone': '555-901-2345', 'address': '901 Nursing Lane', 'date_joined': '2022-07-20'},
            {'name': 'Dr. James Lee', 'email': 'james.lee@hospital.com', 'password': 'lee123', 'role': 'doctor', 'specialization': 'Psychiatry', 'phone': '555-012-3456', 'address': '432 Mind Road', 'date_joined': '2021-12-15'}
        ]
        
        for user_data in users_data:
            hashed_password = self.hash_password(user_data['password'])
            self.cursor.execute('''
                INSERT INTO users (name, email, password, role, specialization, phone, address, date_joined, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['name'],
                user_data['email'],
                hashed_password,
                user_data['role'],
                user_data['specialization'],
                user_data['phone'],
                user_data['address'],
                user_data['date_joined'],
                'active'
            ))
        
        # Populate patients
        patients_data = [
            {'name': 'Alice Thompson', 'email': 'alice.thompson@email.com', 'phone': '555-123-7890', 'address': '123 Main St', 'date_of_birth': '1985-06-15', 'gender': 'Female', 'blood_group': 'A+', 'registration_date': '2022-03-10'},
            {'name': 'Bob Martinez', 'email': 'bob.martinez@email.com', 'phone': '555-234-8901', 'address': '234 Oak Ave', 'date_of_birth': '1978-11-22', 'gender': 'Male', 'blood_group': 'O-', 'registration_date': '2022-04-05'},
            {'name': 'Carol White', 'email': 'carol.white@email.com', 'phone': '555-345-9012', 'address': '345 Pine Rd', 'date_of_birth': '1992-03-30', 'gender': 'Female', 'blood_group': 'B+', 'registration_date': '2022-05-12'},
            {'name': 'David Kim', 'email': 'david.kim@email.com', 'phone': '555-456-0123', 'address': '456 Cedar Ln', 'date_of_birth': '1965-08-17', 'gender': 'Male', 'blood_group': 'AB-', 'registration_date': '2022-06-20'},
            {'name': 'Eva Rodriguez', 'email': 'eva.rodriguez@email.com', 'phone': '555-567-1234', 'address': '567 Maple Dr', 'date_of_birth': '2000-01-25', 'gender': 'Female', 'blood_group': 'A-', 'registration_date': '2022-07-08'},
            {'name': 'Frank Johnson', 'email': 'frank.johnson@email.com', 'phone': '555-678-2345', 'address': '678 Elm St', 'date_of_birth': '1972-12-03', 'gender': 'Male', 'blood_group': 'O+', 'registration_date': '2022-08-15'},
            {'name': 'Grace Liu', 'email': 'grace.liu@email.com', 'phone': '555-789-3456', 'address': '789 Birch Ave', 'date_of_birth': '1990-05-11', 'gender': 'Female', 'blood_group': 'B-', 'registration_date': '2022-09-22'},
            {'name': 'Henry Wilson', 'email': 'henry.wilson@email.com', 'phone': '555-890-4567', 'address': '890 Spruce Rd', 'date_of_birth': '1983-07-19', 'gender': 'Male', 'blood_group': 'AB+', 'registration_date': '2022-10-30'},
            {'name': 'Isabel Garcia', 'email': 'isabel.garcia@email.com', 'phone': '555-901-5678', 'address': '901 Walnut Ln', 'date_of_birth': '1995-09-27', 'gender': 'Female', 'blood_group': 'A+', 'registration_date': '2022-11-14'},
            {'name': 'Jack Brown', 'email': 'jack.brown@email.com', 'phone': '555-012-6789', 'address': '012 Aspen Dr', 'date_of_birth': '1970-04-08', 'gender': 'Male', 'blood_group': 'O-', 'registration_date': '2022-12-05'}
        ]
        
        for patient_data in patients_data:
            self.cursor.execute('''
                INSERT INTO patients (name, email, phone, address, date_of_birth, gender, blood_group, registration_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data['name'],
                patient_data['email'],
                patient_data['phone'],
                patient_data['address'],
                patient_data['date_of_birth'],
                patient_data['gender'],
                patient_data['blood_group'],
                patient_data['registration_date'],
                'active'
            ))
        
        # Populate medical records
        medical_records_data = [
            {'patient_id': 1, 'doctor_id': 1, 'diagnosis': 'Hypertension', 'treatment': 'Prescribed ACE inhibitors', 'notes': 'Patient advised to reduce salt intake and exercise regularly', 'record_date': '2023-01-15'},
            {'patient_id': 2, 'doctor_id': 2, 'diagnosis': 'Migraine', 'treatment': 'Prescribed sumatriptan', 'notes': 'Patient to avoid trigger foods and maintain regular sleep schedule', 'record_date': '2023-02-22'},
            {'patient_id': 3, 'doctor_id': 3, 'diagnosis': 'Bronchitis', 'treatment': 'Prescribed antibiotics and bronchodilator', 'notes': 'Follow-up in two weeks if symptoms persist', 'record_date': '2023-03-10'},
            {'patient_id': 4, 'doctor_id': 6, 'diagnosis': 'Eczema', 'treatment': 'Prescribed topical corticosteroids', 'notes': 'Patient advised to use mild soap and moisturize regularly', 'record_date': '2023-04-05'},
            {'patient_id': 5, 'doctor_id': 8, 'diagnosis': 'Sprained ankle', 'treatment': 'RICE protocol recommended', 'notes': 'X-ray negative for fracture. Physical therapy to start in one week', 'record_date': '2023-05-18'},
            {'patient_id': 6, 'doctor_id': 10, 'diagnosis': 'Generalized anxiety disorder', 'treatment': 'Prescribed SSRIs and recommended CBT', 'notes': 'Patient to return in one month to assess medication effectiveness', 'record_date': '2023-06-23'},
            {'patient_id': 7, 'doctor_id': 1, 'diagnosis': 'Hypercholesterolemia', 'treatment': 'Prescribed statins', 'notes': 'Patient advised on diet modifications and regular exercise', 'record_date': '2023-07-11'},
            {'patient_id': 8, 'doctor_id': 3, 'diagnosis': 'Upper respiratory infection', 'treatment': 'Symptomatic treatment recommended', 'notes': 'Patient advised to rest and increase fluid intake', 'record_date': '2023-08-09'},
            {'patient_id': 9, 'doctor_id': 6, 'diagnosis': 'Acne vulgaris', 'treatment': 'Prescribed topical retinoids and antibiotics', 'notes': 'Patient advised on proper skin care routine', 'record_date': '2023-09-14'},
            {'patient_id': 10, 'doctor_id': 2, 'diagnosis': 'Tension headache', 'treatment': 'Prescribed NSAIDs', 'notes': 'Patient advised to manage stress and maintain good posture', 'record_date': '2023-10-20'}
        ]
        
        for record_data in medical_records_data:
            self.cursor.execute('''
                INSERT INTO medical_records (patient_id, doctor_id, diagnosis, treatment, notes, record_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                record_data['patient_id'],
                record_data['doctor_id'],
                record_data['diagnosis'],
                record_data['treatment'],
                record_data['notes'],
                record_data['record_date']
            ))
        
        # Populate appointments
        # Generate future dates for appointments
        base_date = datetime.datetime.now()
        future_dates = [(base_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 21)]
        times = ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00']
        
        appointments_data = [
            {'patient_id': 1, 'doctor_id': 1, 'appointment_date': future_dates[0], 'appointment_time': '09:00', 'reason': 'Blood pressure check', 'status': 'scheduled'},
            {'patient_id': 2, 'doctor_id': 2, 'appointment_date': future_dates[1], 'appointment_time': '10:30', 'reason': 'Follow-up on migraine treatment', 'status': 'scheduled'},
            {'patient_id': 3, 'doctor_id': 3, 'appointment_date': future_dates[2], 'appointment_time': '14:15', 'reason': 'Bronchitis follow-up', 'status': 'scheduled'},
            {'patient_id': 4, 'doctor_id': 6, 'appointment_date': future_dates[3], 'appointment_time': '11:45', 'reason': 'Skin condition assessment', 'status': 'scheduled'},
            {'patient_id': 5, 'doctor_id': 8, 'appointment_date': future_dates[4], 'appointment_time': '13:30', 'reason': 'Ankle rehabilitation progress', 'status': 'scheduled'},
            {'patient_id': 6, 'doctor_id': 10, 'appointment_date': future_dates[5], 'appointment_time': '15:00', 'reason': 'Therapy session', 'status': 'scheduled'},
            {'patient_id': 7, 'doctor_id': 1, 'appointment_date': future_dates[6], 'appointment_time': '10:00', 'reason': 'Cholesterol level check', 'status': 'scheduled'},
            {'patient_id': 8, 'doctor_id': 3, 'appointment_date': future_dates[7], 'appointment_time': '16:30', 'reason': 'Annual check-up', 'status': 'scheduled'},
            {'patient_id': 9, 'doctor_id': 6, 'appointment_date': future_dates[8], 'appointment_time': '09:45', 'reason': 'Acne treatment follow-up', 'status': 'scheduled'},
            {'patient_id': 10, 'doctor_id': 2, 'appointment_date': future_dates[9], 'appointment_time': '14:00', 'reason': 'Headache consultation', 'status': 'scheduled'}
        ]
        
        for appointment_data in appointments_data:
            self.cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                appointment_data['patient_id'],
                appointment_data['doctor_id'],
                appointment_data['appointment_date'],
                appointment_data['appointment_time'],
                appointment_data['reason'],
                appointment_data['status']
            ))
        
        # Populate prescriptions
        prescriptions_data = [
            {'record_id': 1, 'medication': 'Lisinopril', 'dosage': '10mg', 'frequency': 'Once daily', 'duration': '30 days', 'notes': 'Take in the morning with food'},
            {'record_id': 2, 'medication': 'Sumatriptan', 'dosage': '50mg', 'frequency': 'As needed for migraine', 'duration': '30 days', 'notes': 'Do not exceed 200mg in 24 hours'},
            {'record_id': 3, 'medication': 'Amoxicillin', 'dosage': '500mg', 'frequency': 'Three times daily', 'duration': '10 days', 'notes': 'Complete full course even if feeling better'},
            {'record_id': 3, 'medication': 'Albuterol inhaler', 'dosage': '2 puffs', 'frequency': 'Every 4-6 hours as needed', 'duration': '30 days', 'notes': 'Use spacer for better delivery'},
            {'record_id': 4, 'medication': 'Hydrocortisone cream', 'dosage': 'Thin layer', 'frequency': 'Twice daily', 'duration': '14 days', 'notes': 'Apply to affected areas only'},
            {'record_id': 6, 'medication': 'Sertraline', 'dosage': '50mg', 'frequency': 'Once daily', 'duration': '30 days', 'notes': 'Take in the morning, may cause drowsiness'},
            {'record_id': 7, 'medication': 'Atorvastatin', 'dosage': '20mg', 'frequency': 'Once daily', 'duration': '90 days', 'notes': 'Take in the evening'},
            {'record_id': 8, 'medication': 'Acetaminophen', 'dosage': '500mg', 'frequency': 'Every 6 hours as needed', 'duration': '7 days', 'notes': 'Do not exceed 4000mg in 24 hours'},
            {'record_id': 9, 'medication': 'Tretinoin cream', 'dosage': 'Pea-sized amount', 'frequency': 'Once daily at bedtime', 'duration': '60 days', 'notes': 'Avoid sun exposure, use sunscreen'},
            {'record_id': 10, 'medication': 'Ibuprofen', 'dosage': '400mg', 'frequency': 'Every 6 hours as needed', 'duration': '10 days', 'notes': 'Take with food to minimize stomach irritation'}
        ]
        
        for prescription_data in prescriptions_data:
            self.cursor.execute('''
                INSERT INTO prescriptions (record_id, medication, dosage, frequency, duration, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                prescription_data['record_id'],
                prescription_data['medication'],
                prescription_data['dosage'],
                prescription_data['frequency'],
                prescription_data['duration'],
                prescription_data['notes']
            ))
        
        # Populate billing
        billing_data = [
            {'patient_id': 1, 'record_id': 1, 'amount': 150.00, 'payment_status': 'paid', 'payment_date': '2023-01-15', 'payment_method': 'Credit Card'},
            {'patient_id': 2, 'record_id': 2, 'amount': 200.00, 'payment_status': 'paid', 'payment_date': '2023-02-22', 'payment_method': 'Insurance'},
            {'patient_id': 3, 'record_id': 3, 'amount': 175.50, 'payment_status': 'paid', 'payment_date': '2023-03-10', 'payment_method': 'Cash'},
            {'patient_id': 4, 'record_id': 4, 'amount': 125.00, 'payment_status': 'paid', 'payment_date': '2023-04-05', 'payment_method': 'Insurance'},
            {'patient_id': 5, 'record_id': 5, 'amount': 300.00, 'payment_status': 'pending', 'payment_date': None, 'payment_method': None},
            {'patient_id': 6, 'record_id': 6, 'amount': 225.75, 'payment_status': 'paid', 'payment_date': '2023-06-23', 'payment_method': 'Debit Card'},
            {'patient_id': 7, 'record_id': 7, 'amount': 175.00, 'payment_status': 'paid', 'payment_date': '2023-07-11', 'payment_method': 'Insurance'},
            {'patient_id': 8, 'record_id': 8, 'amount': 100.00, 'payment_status': 'pending', 'payment_date': None, 'payment_method': None},
            {'patient_id': 9, 'record_id': 9, 'amount': 150.00, 'payment_status': 'paid', 'payment_date': '2023-09-14', 'payment_method': 'Credit Card'},
            {'patient_id': 10, 'record_id': 10, 'amount': 125.50, 'payment_status': 'pending', 'payment_date': None, 'payment_method': None}
        ]
        
        for billing_data in billing_data:
            self.cursor.execute('''
                INSERT INTO billing (patient_id, record_id, amount, payment_status, payment_date, payment_method)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                billing_data['patient_id'],
                billing_data['record_id'],
                billing_data['amount'],
                billing_data['payment_status'],
                billing_data['payment_date'],
                billing_data['payment_method']
            ))
        
        # Commit changes and close connection
        self.conn.commit()
        print("Database successfully populated with sample data!")
    
    def close_connection(self):
        self.conn.close()

if __name__ == "__main__":
    populator = DatabasePopulator()
    populator.populate_database()
    populator.close_connection()