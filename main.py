import flet as ft
import sqlite3
import hashlib
import datetime
import subprocess
import sys
import os

class LoginApp:
    def __init__(self):
        self.conn = sqlite3.connect('hospital.db')
        self.cursor = self.conn.cursor()
        self.setup_database()
        
    def setup_database(self):
        self.cursor.execute('''
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
        self.conn.commit()
        
        # Create admin user if it doesn't exist
        self.cursor.execute("SELECT * FROM users WHERE email = 'admin@hospital.com'")
        if not self.cursor.fetchone():
            hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute('''
                INSERT INTO users (name, email, password, role, date_joined, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ("Admin User", "admin@hospital.com", hashed_password, "admin", today, "active"))
            self.conn.commit()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, email, password):
        hashed_password = self.hash_password(password)
        self.cursor.execute('''
            SELECT id, name, email, role, status FROM users 
            WHERE email = ? AND password = ?
        ''', (email, hashed_password))
        user = self.cursor.fetchone()
        
        if user and user[4] == 'active':
            return {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'role': user[3]
            }
        return None
    
    def register_user(self, user_data):
        try:
            # Check if email already exists
            self.cursor.execute("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if self.cursor.fetchone():
                return False, "Email already registered."
                
            hashed_password = self.hash_password(user_data['password'])
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            self.cursor.execute('''
                INSERT INTO users (name, email, password, role, specialization, phone, address, date_joined, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['name'],
                user_data['email'],
                hashed_password,
                user_data['role'],
                user_data.get('specialization', None),
                user_data.get('phone', None),
                user_data.get('address', None),
                today,
                'active'
            ))
            self.conn.commit()
            return True, "Registration successful!"
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def launch_main_app(self, user_data):
        # Create a temporary file to pass user data
        with open('user_session.txt', 'w') as f:
            f.write(f"{user_data['id']}\n")
            f.write(f"{user_data['name']}\n")
            f.write(f"{user_data['email']}\n")
            f.write(f"{user_data['role']}\n")
        
        # Launch main.py
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
            main_path = os.path.join(script_dir, 'app.py')
            subprocess.Popen([sys.executable, main_path])
            return True
        except Exception as e:
            print(f"Error launching main app: {e}")
            return False
    
    def login_page(self, page: ft.Page):
        page.title = "Hospital Management System - Login"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.bgcolor = ft.Colors.WHITE
        
        
        def login_click(e):
            email = email_field.value
            password = password_field.value
            
            if not email or not password:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Please enter both email and password"),
                    bgcolor=ft.Colors.RED_400
                )
                page.snack_bar.open = True
                page.update()
                return
            
            user = self.verify_user(email, password)
            if user:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Login successful! Welcome, {user['name']}"),
                    bgcolor=ft.Colors.GREEN_400
                )
                page.snack_bar.open = True
                page.update()
                
                # Launch main app and close login window
                if self.launch_main_app(user):
                    page.window.close()
            else:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Invalid email or password"),
                    bgcolor=ft.Colors.RED_400
                )
                page.snack_bar.open = True
                page.update()
        
        def go_to_register(e):
            self.register_page(page)
        
        # Login form components
        email_field = ft.TextField(
            label="Email",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.EMAIL,
            width=300,
            autofocus=True
        )
        
        password_field = ft.TextField(
            label="Password",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            on_click=login_click
        )
        
        register_button = ft.TextButton(
            text="Don't have an account? Register here",
            on_click=go_to_register
        )
        
        # Layout
        page.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Hospital Management System", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text("Login to your account", size=16, color=ft.Colors.GREY),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        email_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        password_field,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        login_button,
                        register_button
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                width=500,
                padding=20,
                border_radius=10,
                bgcolor=ft.Colors.WHITE,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=10,
                    color=ft.Colors.BLUE_GREY_300,
                    offset=ft.Offset(0, 0)
                )
            )
        ]
        page.update()
    
    def register_page(self, page):
        page.title = "Hospital Management System - Register"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.bgcolor = ft.Colors.WHITE
        
        def register_click(e):
            # Validate form data
            if not name_field.value or not email_field.value or not password_field.value or not confirm_password_field.value:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Please fill in all required fields"),
                    bgcolor=ft.Colors.RED_400
                )
                page.snack_bar.open = True
                page.update()
                return
            
            if password_field.value != confirm_password_field.value:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Passwords do not match"),
                    bgcolor=ft.Colors.RED_400
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Prepare user data
            user_data = {
                'name': name_field.value,
                'email': email_field.value,
                'password': password_field.value,
                'role': role_dropdown.value,
                'phone': phone_field.value,
                'address': address_field.value
            }
            
            # Add specialization if role is doctor
            if role_dropdown.value == 'doctor':
                user_data['specialization'] = specialization_field.value
            
            # Register user
            success, message = self.register_user(user_data)
            
            if success:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(message),
                    bgcolor=ft.Colors.GREEN_400
                )
                page.snack_bar.open = True
                page.update()
                
                # Go back to login page after successful registration
                page.snack_bar.action = ft.TextButton("Login Now", on_click=lambda _: self.login_page(page))
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(message),
                    bgcolor=ft.Colors.RED_400
                )
                page.snack_bar.open = True
                page.update()
        
        def go_to_login(e):
            self.login_page(page)
        
        def update_specialization_visibility(e):
            specialization_container.visible = role_dropdown.value == "doctor"
            page.update()
        
        # Register form components
        name_field = ft.TextField(
            label="Full Name",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.PERSON,
            width=300,
            autofocus=True
        )
        
        email_field = ft.TextField(
            label="Email",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.EMAIL,
            width=300
        )
        
        password_field = ft.TextField(
            label="Password",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        confirm_password_field = ft.TextField(
            label="Confirm Password",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        role_dropdown = ft.Dropdown(
            label="Role",
            width=300,
            options=[
                ft.dropdown.Option("nurse", "Nurse"),
                ft.dropdown.Option("doctor", "Doctor")
            ],
            value="patients",
            on_change=update_specialization_visibility
        )
        
        specialization_field = ft.TextField(
            label="Specialization",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.MEDICAL_SERVICES,
            width=300
        )
        
        specialization_container = ft.Container(
            content=specialization_field,
            visible=False
        )
        
        phone_field = ft.TextField(
            label="Phone Number",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.PHONE,
            width=300
        )
        
        address_field = ft.TextField(
            label="Address",
            border=ft.InputBorder.OUTLINE,
            prefix_icon=ft.Icons.HOME,
            width=300,
            multiline=True,
            min_lines=2,
            max_lines=3
        )
        
        register_button = ft.ElevatedButton(
            text="Register",
            width=300,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            on_click=register_click
        )
        
        login_button = ft.TextButton(
            text="Already have an account? Login here",
            on_click=go_to_login
        )
        
        # Layout
        page.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Hospital Management System", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text("Create new account", size=16, color=ft.Colors.GREY),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        name_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        email_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        password_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        confirm_password_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        role_dropdown,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        specialization_container,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        phone_field,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        address_field,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        register_button,
                        login_button
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO
                ),
                width=550,
                height=600,
                padding=20,
                border_radius=10,
                bgcolor=ft.Colors.WHITE,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=10,
                    color=ft.Colors.BLUE_GREY_300,
                    offset=ft.Offset(0, 0)
                )
            )
        ]
        page.update()

def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.center()
    app = LoginApp()
    app.login_page(page)

if __name__ == "__main__":
    ft.app(target=main)