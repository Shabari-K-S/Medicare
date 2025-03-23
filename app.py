from flet import *
from db_utils import HospitalDB
from datetime import datetime
import google.generativeai as genai
import threading
import os
import sys
import subprocess
import json
from typing import List, Dict, Any, Optional
import time

class ChatManager:
    """Manages chat storage and retrieval"""
    
    def __init__(self, file_path="chat.json"):
        self.file_path = file_path
        self.chats = self._load_chats()
    
    def _load_chats(self) -> Dict[str, Any]:
        """Load chats from JSON file"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                # Return empty structure if file is corrupted
                return {"chats": []}
        return {"chats": []}
    
    def save_chats(self):
        """Save chats to JSON file"""
        with open(self.file_path, 'w') as file:
            json.dump(self.chats, file, indent=2)
    
    def get_chat_list(self) -> List[Dict[str, Any]]:
        """Get list of all chats"""
        return self.chats.get("chats", [])
    
    def create_new_chat(self, title: str = None) -> str:
        """Create a new chat and return its ID"""
        chat_id = f"chat_{len(self.get_chat_list()) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if not title:
            title = f"Chat {len(self.get_chat_list()) + 1}"
        
        new_chat = {
            "id": chat_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        self.chats.setdefault("chats", []).append(new_chat)
        self.save_chats()
        return chat_id
    
    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chat by ID"""
        for chat in self.get_chat_list():
            if chat["id"] == chat_id:
                return chat
        return None
    
    def add_message(self, chat_id: str, sender: str, message: str):
        """Add a message to a specific chat"""
        chat = self.get_chat(chat_id)
        if chat:
            chat["messages"].append({
                "sender": sender,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            chat["updated_at"] = datetime.now().isoformat()
            
            # Update title for new chats based on first user message
            if len(chat["messages"]) == 1 and sender == "You":
                # Truncate long messages for the title
                title = message[:30] + "..." if len(message) > 30 else message
                chat["title"] = title
                
            self.save_chats()
    
    def update_chat_title(self, chat_id: str, new_title: str):
        """Update the title of a chat"""
        chat = self.get_chat(chat_id)
        if chat:
            chat["title"] = new_title
            self.save_chats()
    
    def delete_chat(self, chat_id: str):
        """Delete a chat by ID"""
        self.chats["chats"] = [chat for chat in self.get_chat_list() if chat["id"] != chat_id]
        self.save_chats()

def chatbot_page(page: Page) -> Container:
    # Enhanced blue color scheme
    primary_color = "#1976D2"  # Deeper blue for primary elements
    secondary_color = "#2196F3"  # Medium blue for secondary elements
    accent_color = "#42A5F5"    # Lighter blue for accents
    bg_color = "#F5F7FA"        # Light background
    chat_user_bubble = "#E3F2FD"  # Very light blue for user bubbles
    chat_ai_bubble = "#F8F9FA"    # Off-white for AI bubbles
    
    # Initialize chat manager and model
    chat_manager = ChatManager()
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Current chat session data
    current_chat = {
        "id": None,
        "session": None
    }
    
    # Chat history display
    chat_history = Column(
        spacing=10,
        scroll=ScrollMode.AUTO,
        expand=True,
        width=page.window.width * 0.70,
        height=page.window.height * 0.44
    )
    
    # Add messages to chat UI
    def add_message(sender_name, message_text, save_to_history=True):
        bubble_color = chat_user_bubble if sender_name == "You" else chat_ai_bubble
        alignment_right = True if sender_name == "You" else False
            
        message_container = Container(
            content=Column([
                Text(
                    sender_name, 
                    size=12, 
                    weight="bold",
                    color=primary_color if sender_name != "You" else Colors.BLACK87,
                    text_align="right" if sender_name == "You" else "left"
                ),
                Text(
                    message_text, 
                    size=14, 
                    selectable=True
                ) if sender_name == "You" else Markdown( message_text, selectable=True, extension_set=MarkdownExtensionSet.GITHUB_WEB)
            ]),
            padding=padding.all(12),
            bgcolor=bubble_color,
            border_radius=10,
            width=page.width * 0.5 if page.width else 280,
            alignment=alignment.center_right if sender_name == "You" else alignment.center_left,
            shadow={"blur": 2, "color": Colors.BLACK12, "offset": (0, 1)}
        )
        
        row = Row(
            [message_container],
            alignment="end" if alignment_right else "start"
        )
        
        chat_history.controls.append(row)
        page.update()
        # Scroll to bottom
        chat_history.scroll_to(offset=chat_history.height)
        
        # Save to chat history if needed
        if save_to_history and current_chat["id"]:
            chat_manager.add_message(current_chat["id"], sender_name, message_text)
    
    # Thinking indicator
    thinking_indicator = ProgressRing(
        width=20, 
        height=20, 
        color=primary_color,
        visible=False
    )
    
    # Send message handler
    def send_message(e):
        user_text = message_input.value.strip()
        if not user_text:
            return
        
        # Create a new chat if none exists
        if not current_chat["id"]:
            current_chat["id"] = chat_manager.create_new_chat()
            current_chat["session"] = model.start_chat(history=[])
            update_chat_dropdown()
            chat_dropdown.value = current_chat["id"]
            
        add_message("You", user_text)
        message_input.value = ""
        message_input.disabled = True
        send_button.disabled = True
        thinking_indicator.visible = True
        page.update()
        


        # Use standard Python threading for background processing
        def process_response():
            try:
                prompt = f"""
# Medical Check-up Assistant Prompt

You are a Medical Check-up Assistant AI designed to support nurses and doctors during routine patient examinations and simple check-ups. Your role is to provide helpful information, reminders, and assistance with basic medical protocols to make routine appointments more efficient and thorough.

## Primary Functions

- **Vital Signs Guidance**: Provide normal ranges and interpretation assistance for temperature, blood pressure, pulse, respiratory rate, and oxygen saturation.

- **Checklist Support**: Help track completion of routine check-up steps to ensure nothing is overlooked.

- **Documentation Assistance**: Offer templates and suggestions for routine medical notes and patient instructions.

- **Patient Information**: Help retrieve and organize basic patient information during consultations.

- **Routine Questions**: Suggest standard screening questions appropriate for different patient demographics.

## How to Respond

When assisting medical staff during check-ups:

1. **Be Concise**: Provide brief, clear responses that don't interrupt workflow.

2. **Be Practical**: Focus on immediately useful information for routine visits.

3. **Be Supportive**: Offer reminders and suggestions without being prescriptive.

4. **Be Organized**: Present information in a structured, easy-to-scan format.

5. **Be Respectful**: Recognize the medical staff's expertise and position as the primary care provider.

## Example Scenarios

### Scenario 1: Vital Sign Check
**Staff**: "What's the normal blood pressure range for a 65-year-old patient?"

**Assistant**: "Normal BP for 65-year-old adults: 
- Ideal: Below 120/80 mmHg
- Normal: Up to 129/84 mmHg
- Elevated: 130-139/85-89 mmHg
- High: 140/90 mmHg or higher

Would you like age-specific considerations for this patient?"

### Scenario 2: Routine Check-up Reminders
**Staff**: "Help me with a standard adult check-up checklist."

**Assistant**: "Standard Adult Check-up Checklist:
- Vital signs (BP, pulse, temp, respiration)
- Height and weight (calculate BMI)
- Medical history review/updates
- Medication review
- Basic physical examination
- Preventive screening questions
- Age-appropriate screenings due
- Immunization review
- Lifestyle discussion (diet, exercise, sleep)
- Any specific patient concerns

Need any specific details for any of these items?"

### Scenario 3: Simple Documentation
**Staff**: "I need a template for normal findings in a routine physical."

**Assistant**: "Basic Normal Findings Template:
- General: Alert, oriented, no acute distress
- Vital signs: Within normal limits
- HEENT: Normocephalic, PERRLA, TMs intact, oropharynx clear
- Neck: Supple, no lymphadenopathy, thyroid normal
- Chest: Clear to auscultation bilaterally
- Heart: RRR, no murmurs/gallops/rubs
- Abdomen: Soft, non-tender, no organomegaly
- Extremities: No edema, pulses intact
- Skin: No rashes or lesions
- Neuro: CN II-XII intact, normal gait

Would you like me to expand any section?"

## Limitations to Acknowledge

- I do not diagnose conditions or interpret test results
- I do not prescribe or recommend specific treatments
- I cannot access patient records unless specifically shared
- I am meant to assist with routine matters, not complex or emergency situations
- I defer to the medical professional's judgment at all times

I'm here to make routine check-ups more efficient by providing quick reference information and organizational support. How can I assist with today's patient appointments?

prompt: {user_text}
"""
                # Send message to Gemini chat session
                response = current_chat["session"].send_message(prompt)
                response_text = response.text
            except Exception as e:
                response_text = f"Sorry, I encountered an error: {str(e)}"
            
            # Update UI on the main thread
            def update_ui():
                add_message("Gemini", response_text)
                message_input.disabled = False
                send_button.disabled = False
                thinking_indicator.visible = False
                page.update()
            
            update_ui()
        
        # Start a thread for background processing
        threading.Thread(target=process_response).start()
    
    # Create new chat button handler
    def create_new_chat(e):
        # Reset the UI
        chat_history.controls.clear()
        
        # Create a new chat session
        current_chat["id"] = chat_manager.create_new_chat()
        current_chat["session"] = model.start_chat(history=[])
        
        # Update dropdown and select the new chat
        update_chat_dropdown()
        chat_dropdown.value = current_chat["id"]
        
        # Add welcome message
        add_welcome_message()
        page.update()
    
    # Load chat handler
    def load_chat(e):
        selected_chat_id = chat_dropdown.value
        if not selected_chat_id or selected_chat_id == current_chat["id"]:
            return
            
        # Clear the current chat display
        chat_history.controls.clear()
        
        # Load the selected chat
        chat_data = chat_manager.get_chat(selected_chat_id)
        if chat_data:
            # Create a new chat session
            current_chat["id"] = selected_chat_id
            current_chat["session"] = model.start_chat(history=[])
            
            # Display messages
            for msg in chat_data["messages"]:
                add_message(msg["sender"], msg["message"], save_to_history=False)
            
            # If empty chat, add welcome message
            if not chat_data["messages"]:
                add_welcome_message()
        
        page.update()
    
    # Delete current chat
    def delete_current_chat(e):
        if current_chat["id"]:
            chat_manager.delete_chat(current_chat["id"])
            current_chat["id"] = None
            current_chat["session"] = None
            
            # Clear the UI
            chat_history.controls.clear()
            
            # Update the dropdown
            update_chat_dropdown()
            
            # Create a new chat
            if len(chat_manager.chats) == 0:
                create_new_chat(None)
    
    # Update chat dropdown options
    def update_chat_dropdown():
        chat_list = chat_manager.get_chat_list()
        chat_dropdown.options = [
            dropdown.Option(key=chat["id"], text=chat["title"]) 
            for chat in sorted(chat_list, key=lambda x: x["updated_at"], reverse=True)
        ]
        
        # Add a default option if no chats exist
        if not chat_dropdown.options:
            chat_dropdown.options = [dropdown.Option(key="new", text="New Chat")]

        page.update()

    # Message input field
    message_input = TextField(
        hint_text="Type a message...",
        border_radius=8,
        expand=True,
        on_submit=send_message,
        border_color=accent_color,
        focused_border_color=primary_color,
    )
    
    # Simple send button
    send_button = IconButton(
        icon=Icons.SEND_ROUNDED,
        icon_color=Colors.WHITE,
        bgcolor=primary_color,
        on_click=send_message,
    )

    # Chat dropdown selector
    chat_dropdown = Dropdown(
        width=page.window.width * 0.50 if page.window else 300,
        label="Select a chat",
        border_color=accent_color,
        color=primary_color,
        on_click=load_chat,
    )

    update_chat_dropdown()
    

    # Create new chat button
    new_chat_button = ElevatedButton(
        text="New Chat",
        icon=Icons.ADD,
        on_click=create_new_chat,
        bgcolor=primary_color,
        color=Colors.WHITE,
    )
    
    # Delete chat button
    delete_chat_button = IconButton(
        icon=Icons.DELETE_OUTLINE,
        icon_color=Colors.RED_400,
        tooltip="Delete current chat",
        on_click=delete_current_chat,
    )
    
    # Add welcome message
    def add_welcome_message():
        welcome_message = "Hello! I'm your Gemini-powered assistant. How can I help you today?"
        add_message("Gemini", welcome_message)
        
        # Initialize chat session with a system message
        try:
            if current_chat["session"]:
                current_chat["session"].send_message("You are a helpful AI assistant. Respond concisely and accurately.")
        except Exception:
            # Silently handle any initialization errors
            pass
    
    # Initialize the UI when the page is mounted
    def init_ui(e):
        # Load existing chats
        update_chat_dropdown()
        
        # Create a new chat if none exist
        if not chat_manager.get_chat_list():
            create_new_chat(None)
        else:
            # Load the most recent chat
            most_recent = sorted(
                chat_manager.get_chat_list(), 
                key=lambda x: x["updated_at"], 
                reverse=True
            )[0]
            
            current_chat["id"] = most_recent["id"]
            current_chat["session"] = model.start_chat(history=[])
            chat_dropdown.value = current_chat["id"]
            
            # Load the messages
            for msg in most_recent["messages"]:
                add_message(msg["sender"], msg["message"], save_to_history=False)
            
            # If empty chat, add welcome message
            if not most_recent["messages"]:
                add_welcome_message()
    
    # Set the initialization function
    page.on_mount = init_ui
    
    # Main layout
    return Container(
        content=Column([
            # Header with chat selector
            Container(
                content=Row([
                    Text(
                        "Gemini Chat",
                        size=24,
                        weight="bold",
                        color=primary_color,
                    ),
                ]),
                padding=padding.only(bottom=10),
            ),
            
            # Chat selector and controls
            Container(
                content=Row([
                    chat_dropdown,
                    new_chat_button,
                    delete_chat_button,
                ], 
                spacing=10,
                alignment="center"),
                padding=padding.only(bottom=15),
            ),
            
            # Chat history container
            Container(
                content=chat_history,
                expand=True,
                bgcolor=bg_color,
                border_radius=12,
                padding=15,
                border={"width": 1, "color": Colors.BLACK12},
            ),
            
            # Message input and send button
            Container(
                content=Row(
                    [message_input, thinking_indicator, send_button],
                    spacing=10,
                    alignment="center",
                ),
                padding=padding.only(top=15),
            )
        ]),
        padding=20,
        expand=True,
        bgcolor=Colors.WHITE,
    )

def create_dashboard(chart_data, user_info=None, page: Page = None, db:HospitalDB = None):
    """
    Create a dashboard UI component with key metrics and visualizations
    
    Args:
        chart_data: Dictionary containing all chart data for visualizations
        user_info: Dictionary with information about the current user
        
    Returns:
        Dashboard container with all UI components
    """
    # Set default user info if not provided

    
    if user_info is None:
        user_info = {"name": "Smith", "role": "Doctor"}

    def appointments_form(e):
        page.overlay.append(create_form(form_type="appointment", page=page))
        page.update()
    
    def prescription_form(e):
        page.overlay.append(create_form(form_type="prescription", page=page))
        page.update()

    def billing_form(e):
        page.overlay.append(create_form(form_type="billing", page=page))
        page.update()

    def medical_record_form(e):
        page.overlay.append(create_form(form_type="medical_record", page=page))
        page.update()

    # Create header section
    header = Container(
        content=Row(
            controls=[
                Column(
                    controls=[
                        Text(
                            "Dashboard",
                            size=24,
                            color=Colors.BLACK87,
                            weight="bold",
                        ),
                        Text(
                            f"Welcome back, Dr. {user_info['name']}",
                            size=16,
                            color=Colors.GREY_600,
                        ),
                    ],
                    spacing=5,
                ),
                Row(
                    controls=[
                        ElevatedButton(
                            text="New Appointment",
                            icon=Icons.CALENDAR_MONTH,
                            bgcolor=Colors.BLUE_700,
                            color=Colors.WHITE,
                            on_click=appointments_form

                        ),
                        ElevatedButton(
                            text="New Medical Record",
                            icon=Icons.MEDICAL_SERVICES,
                            bgcolor=Colors.BLUE_700,
                            color=Colors.WHITE,
                            on_click=medical_record_form
                        ),
                        ElevatedButton(
                            text="New Prescription", 
                            icon=Icons.MEDICATION,
                            bgcolor=Colors.BLUE_700,
                            color=Colors.WHITE,
                            on_click=prescription_form
                        ),
                        ElevatedButton(
                            text="New Billing",
                            icon=Icons.RECEIPT_LONG,
                            bgcolor=Colors.BLUE_700,
                            color=Colors.WHITE,
                            on_click=billing_form
                        ),
                    ],
                    spacing=10,
                ),
            ],
            alignment="spaceBetween",
        ),
        padding=padding.all(20),
        bgcolor=Colors.WHITE,
        border_radius=BorderRadius(
            top_left=10,
            bottom_left=10,
            top_right=10,
            bottom_right=10,
        ),
    )
    
    # Create metrics cards
    metrics = Row(
        controls=[
            # Total Patients card
            Container(
                content=Row(
                    controls=[
                        Column(
                            controls=[
                                Text("Total Patients", size=16, color=Colors.GREY_600),
                                Text(f"{chart_data.get("total_patients")}", size=24, color=Colors.BLACK87, weight="bold"),
                                Text(f"+{chart_data.get("new_patients")} new today", size=14, color=Colors.GREEN_500),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        Container(
                            content=Icon(
                                Icons.PEOPLE_OUTLINE_ROUNDED, 
                                color=Colors.BLUE_700,
                                size=24,
                            ),
                            padding=padding.all(12),
                            bgcolor=Colors.BLUE_100,
                            border_radius=BorderRadius(
                                top_left=10,
                                bottom_left=10,
                                top_right=10,
                                bottom_right=10,
                            ),
                        ),
                    ],
                    alignment="center",
                ),
                padding=padding.all(20),
                bgcolor=Colors.WHITE,
                border_radius=BorderRadius(
                    top_left=10,
                    bottom_left=10,
                    top_right=10,
                    bottom_right=10,
                ),
                expand=True,
            ),
            
            # Appointments card
            Container(
                content=Row(
                    controls=[
                        Column(
                            controls=[
                                Text("Appointments", size=16, color=Colors.GREY_600),
                                Text(f"{chart_data.get("total_appointments","")}", size=24, color=Colors.BLACK87, weight="bold"),
                                Text(f"+{chart_data.get("new_appointments","")} scheduled today", size=14, color=Colors.GREEN_500),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        Container(
                            content=Icon(
                                Icons.CALENDAR_MONTH, 
                                color=Colors.BLUE_700,
                                size=24,
                            ),
                            padding=padding.all(12),
                            bgcolor=Colors.BLUE_100,
                            border_radius=BorderRadius(
                                top_left=10,
                                bottom_left=10,
                                top_right=10,
                                bottom_right=10,
                            ),
                        ),
                    ],
                    alignment="center",
                ),
                padding=padding.all(20),
                bgcolor=Colors.WHITE,
                border_radius=BorderRadius(
                    top_left=10,
                    bottom_left=10,
                    top_right=10,
                    bottom_right=10,
                ),
                expand=True,
            ),
            
            # Operations card
            Container(
                content=Row(
                    controls=[
                        Column(
                            controls=[
                                Text("Operations", size=16, color=Colors.GREY_600),
                                Text(f"{chart_data.get("total_operations","")}", size=24, color=Colors.BLACK87, weight="bold"),
                                Text(f"+{chart_data.get("new_operations","")} this week", size=14, color=Colors.GREEN_500),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        Container(
                            content=Icon(
                                Icons.AUTO_GRAPH, 
                                color=Colors.BLUE_700,
                                size=24,
                            ),
                            padding=padding.all(12),
                            bgcolor=Colors.BLUE_100,
                            border_radius=BorderRadius(
                                top_left=10,
                                bottom_left=10,
                                top_right=10,
                                bottom_right=10,
                            ),
                        ),
                    ],
                    alignment="center",
                ),
                padding=padding.all(20),
                bgcolor=Colors.WHITE,
                border_radius=BorderRadius(
                    top_left=10,
                    bottom_left=10,
                    top_right=10,
                    bottom_right=10,
                ),
                expand=True,
            ),
            
            # Wait Time card
            Container(
                content=Row(
                    controls=[
                        Column(
                            controls=[
                                Text("Avg Wait Time", size=16, color=Colors.GREY_600),
                                Text(f"{chart_data.get("avg_wait_time","")}", size=24, color=Colors.BLACK87, weight="bold"),
                                Text("-2 min from last week", size=14, color=Colors.GREEN_500),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        Container(
                            content=Icon(
                                Icons.TIMER, 
                                color=Colors.BLUE_700,
                                size=24,
                            ),
                            padding=padding.all(12),
                            bgcolor=Colors.BLUE_100,
                            border_radius=BorderRadius(
                                top_left=10,
                                bottom_left=10,
                                top_right=10,
                                bottom_right=10,
                            ),
                        ),
                    ],
                    alignment="center",
                ),
                padding=padding.all(20),
                bgcolor=Colors.WHITE,
                border_radius=BorderRadius(
                    top_left=10,
                    bottom_left=10,
                    top_right=10,
                    bottom_right=10,
                ),
                expand=True,
            ),
        ],
        spacing=15,
    )
    
    department_chart_data = db.get_department_performance()
    department_chart_metrics = db.get_department_performance_metrics()

    print(department_chart_data, department_chart_metrics)

    # Department Performance Chart
    department_chart = create_department_chart(chart_data.get("department_performance", department_chart_data))
    
    recent_Activity_data = db.get_recent_activity(3)

    print(recent_Activity_data)

    # Recent Activity Timeline
    activity_timeline = create_activity_timeline(chart_data.get("recent_activity", recent_Activity_data))
    
    appointments_list_data = db.get_todays_top_appointments()

    print(appointments_list_data)

    # Today's Appointments List
    appointments_list = create_appointments_list(chart_data.get("today_appointments", appointments_list_data))
    
    # Layout the charts in a responsive grid
    charts_grid = Container(
        content=Column(
            controls=[
                # Top row
                Row(
                    controls=[
                        # Top left
                        department_chart,
                        # Top right
                        activity_timeline,
                    ],
                    spacing=15,
                    expand=True,
                ),
                # Bottom row
                Row(
                    controls=[
                        # Bottom left
                        appointments_list,
                    ],
                    spacing=15,
                    expand=True,
                ),
            ],
            spacing=15,
            expand=True,
        ),
        padding=15,
        expand=True,
    )
    
    # Combine all sections into the main dashboard
    dashboard = Container(
        content=Column(
            controls=[
                header,
                Container(height=15),  # Spacer
                metrics,
                Container(height=15),  # Spacer
                charts_grid,
            ],
            spacing=0,
        ),
        padding=padding.all(20),
        bgcolor=Colors.GREY_100,
        expand=True,
    )
    
    return dashboard

def create_department_chart(data):
    """Create department performance chart component"""
    # If no data, create sample data
    if not data:
        data = [
            {"department": "Cardiology", "efficiency": 85},
            {"department": "Neurology", "efficiency": 78},
            {"department": "Pediatrics", "efficiency": 92},
            {"department": "Orthopedics", "efficiency": 73},
            {"department": "Oncology", "efficiency": 80}
        ]
    
    # Create progress bars for each department
    department_rows = []
    
    for dept in data:
        dept_name = dept.get("department", "Unknown")
        efficiency = dept.get("efficiency", 0)
        
        department_rows.append(
            Row(
                controls=[
                    Text(dept_name, size=14, color=Colors.BLACK87, expand=True),
                    Text(f"{efficiency}%", size=14, color=Colors.BLUE_700),
                ],
                alignment="spaceBetween",
            )
        )
        
        department_rows.append(
            ProgressBar(
                value=efficiency/100,
                bgcolor=Colors.BLUE_100,
                color=Colors.BLUE_700,
                height=10,
            )
        )
    
    # Add a "View Details" link at the bottom
    department_rows.append(
        Container(
            content=Text(
                "View Details",
                size=12,
                color=Colors.BLUE_700,
            ),
            margin=margin.only(top=10),
            alignment=alignment.center,
        )
    )
    
    # Return the chart container
    return Container(
        content=Column(
            controls=[
                Text(
                    "Department Performance",
                    size=18,
                    color=Colors.BLACK87,
                    weight="bold",
                ),
                Text(
                    "Weekly efficiency metrics",
                    size=14,
                    color=Colors.GREY_600,
                ),
                Container(height=10),  # Spacer
                Column(controls=department_rows, spacing=10),
            ],
            spacing=5,
        ),
        padding=padding.all(20),
        border_radius=BorderRadius(
            top_left=10,
            bottom_left=10,
            top_right=10,
            bottom_right=10,
        ),
        bgcolor=Colors.WHITE,
        expand=True,
    )

def create_activity_timeline(data):
    """Create recent activity timeline component"""
    # If no data, create sample data
    if not data:
        data = [
            {
                "type": "new_patient",
                "title": "New patient admitted",
                "description": "Sarah Johnson was registered",
                "timestamp": "2025-03-22T09:15:00"
            },
            {
                "type": "appointment",
                "title": "Appointment scheduled",
                "description": "Appointment for Michael Davis with Dr. Wilson",
                "timestamp": "2025-03-22T08:45:00"
            },
            {
                "type": "medical_record",
                "title": "Patient discharged",
                "description": "Robert Thompson was discharged from Orthopedics",
                "timestamp": "2025-03-22T07:30:00"
            }
        ]
    
    # Get icon for activity type
    def get_activity_icon(activity_type):
        if activity_type == "new_patient":
            return Icons.PERSON_ADD
        elif activity_type == "appointment":
            return Icons.CALENDAR_TODAY
        elif activity_type == "medical_record":
            return Icons.MEDICAL_SERVICES
        else:
            return Icons.NOTIFICATIONS
    
    # Create activity items for the timeline
    activity_rows = []
    
    for activity in data:
        activity_type = activity.get("type", "unknown")
        title = activity.get("title", "Unknown activity")
        description = activity.get("description", "")
        
        # Add relative time (simplified)
        relative_time = "Just now"
        if "timestamp" in activity:
            timestamp = activity.get("timestamp", "")
            if "09:" in timestamp:
                relative_time = "1 hour ago"
            elif "08:" in timestamp:
                relative_time = "2 hours ago"
            elif "07:" in timestamp:
                relative_time = "3 hours ago"
        
        # Activity row with icon
        activity_rows.append(
            Container(
                content=Row(
                    controls=[
                        Container(
                            content=Icon(
                                get_activity_icon(activity_type),
                                color=Colors.WHITE,
                                size=16,
                            ),
                            bgcolor=Colors.BLUE_700,
                            padding=padding.all(10),
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                        Container(
                            content=Column(
                                controls=[
                                    Text(
                                        title,
                                        size=14,
                                        color=Colors.BLACK87,
                                        weight="bold",
                                    ),
                                    Text(
                                        description,
                                        size=12,
                                        color=Colors.GREY_700,
                                    ),
                                    Text(
                                        relative_time,
                                        size=11,
                                        color=Colors.GREY_500,
                                    ),
                                ],
                                spacing=2,
                                alignment=alignment.top_center,
                            ),
                            margin=margin.only(left=10),
                            expand=True,
                        ),
                    ],
                    alignment=alignment.top_left,
                ),
                margin=margin.only(top=5, bottom=5),
            )
        )
    
    # Add a "View All Activity" link at the bottom
    activity_rows.append(
        Container(
            content=Text(
                "View All Activity",
                size=12,
                color=Colors.BLUE_700,
            ),
            margin=margin.only(top=10),
            alignment=alignment.center,
        )
    )
    
    # Return the chart container
    return Container(
        content=Column(
            controls=[
                Text(
                    "Recent Activity",
                    size=18,
                    color=Colors.BLACK87,
                    weight="bold",
                ),
                Text(
                    "Latest system notifications",
                    size=14,
                    color=Colors.GREY_600,
                ),
                Container(height=10),  # Spacer
                Column(controls=activity_rows, spacing=5),
            ],
            spacing=5,
        ),
        padding=padding.all(20),
        border_radius=BorderRadius(
            top_left=10,
            bottom_left=10,
            top_right=10,
            bottom_right=10,
        ),
        bgcolor=Colors.WHITE,
        expand=True,
    )

def create_appointments_list(data):
    """Create today's appointments list component"""
    # If no data, create sample data
    if not data:
        if not data:
            return Container(
                content=Column(
                    controls=[
                        Text("Today's Appointment", size=18, weight="bold"),
                        Text("No appointments today", size=14, color=Colors.GREY_600, text_align="center")
                    ]
                ),
                padding=padding.all(20),
                bgcolor=Colors.WHITE,
                border_radius=BorderRadius(8, 8, 8, 8),
            )
    # Create appointment items for the list
    appointment_rows = []
    
    for appointment in data:
        patient_name = appointment.get("patient_name", "Unknown Patient")
        time_str = appointment.get("appointment_time", "Unknown Time")
        
        # Format doctor name
        doctor_name = appointment.get("doctor_name", "Unknown Doctor")
        doctor_display = doctor_name
        if " " in doctor_name and "Dr." not in doctor_name:
            doctor_display = f"Dr. {doctor_name.split()[-1]}"
        
        # Format time display
        time_display = time_str
        # If it's already in format like "9:00 AM"
        if ":" in time_str and ("AM" in time_str or "PM" in time_str):
            hour, minute_ampm = time_str.split(":", 1)
            minute = minute_ampm.split()[0]
            ampm = minute_ampm.split()[1]
            
            # Calculate end time (assume 30 min appointments)
            hour_int = int(hour)
            minute_int = int(minute)
            
            end_minute = (minute_int + 30) % 60
            end_hour = hour_int + 1 if end_minute < minute_int else hour_int
            
            # Handle AM/PM transition
            end_ampm = ampm
            if hour_int == 11 and end_hour == 12:
                end_ampm = "PM" if ampm == "AM" else "AM"
            
            # Format the display
            time_display = f"{time_str} - {end_hour}:{end_minute:02d} {end_ampm}"
        
        # Add appointment to list
        appointment_rows.append(
            Container(
                content=Row(
                    controls=[
                        Container(
                            content=Icon(
                                Icons.PERSON,
                                color=Colors.BLUE_700,
                                size=16,
                            ),
                            padding=padding.all(12),
                            bgcolor=Colors.BLUE_100,
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                        Container(
                            content=Column(
                                controls=[
                                    Text(
                                        patient_name,
                                        size=14,
                                        color=Colors.BLACK87,
                                        weight="bold",
                                    ),
                                    Text(
                                        doctor_display,
                                        size=12,
                                        color=Colors.GREY_700,
                                    ),
                                    Text(
                                        time_display,
                                        size=11,
                                        color=Colors.GREY_500,
                                    ),
                                ],
                                spacing=2,
                                alignment=alignment.top_left,
                            ),
                            margin=margin.only(left=10),
                            expand=True,
                        ),
                        Container(
                            content=ElevatedButton(
                                text="Upcoming",
                                bgcolor=Colors.BLUE_50,
                                color=Colors.BLUE_700,
                                height=32,
                            ),
                        ),
                    ],
                    alignment=alignment.center,
                ),
                margin=margin.only(top=5, bottom=5),
            )
        )
    
    # Add a "Show More" button at the bottom
    appointment_rows.append(
        Container(
            content=Text(
                "Show More",
                size=12,
                color=Colors.BLUE_700,
            ),
            margin=margin.only(top=10),
            alignment=alignment.center,
        )
    )
    
    # Return the appointments list container
    return Container(
        content=Column(
            controls=[
                Row(
                    controls=[
                        Text(
                            "Today's Appointments",
                            size=18,
                            color=Colors.BLACK87,
                            weight="bold",
                            expand=True,
                        ),
                        Text(
                            "View all",
                            size=12,
                            color=Colors.BLUE_700,
                        ),
                    ],
                    alignment="spaceBetween",
                ),
                Text(
                    f"You have {len(data)} appointments scheduled for today",
                    size=14,
                    color=Colors.GREY_600,
                ),
                Container(height=10),  # Spacer
                Column(controls=appointment_rows, spacing=10),
            ],
            spacing=5,
        ),
        padding=padding.all(20),
        border_radius=BorderRadius(
            top_left=10,
            bottom_left=10,
            top_right=10,
            bottom_right=10,
        ),
        bgcolor=Colors.WHITE,
        expand=True,
    )

def create_form(form_type, page:Page):
    """
    Universal form creation method for all form types - now creates a modal overlay
    
    Args:
        form_type: String indicating which form to create ("appointment", "prescription", "billing", "medical_record")
        page_state: State management for showing/hiding forms
        page: Page object for updating the UI
        
    Returns:
        Container with the appropriate form content as a modal overlay
    """
    # Initialize database connection
    db = HospitalDB()
    
    # Get common data needed for most forms
    patients = db.get_all_patients()
    doctors = db.get_all_users(role="doctor")
    patient_options = [dropdown.Option(key=str(p["id"]), text=p["name"]) for p in patients]
    doctor_options = [dropdown.Option(key=str(d["id"]), text=d["name"]) for d in doctors]
    
    # Form configuration based on type
    form_config = {
        "appointment": {
            "title": "Schedule New Appointment",
            "submit_text": "Schedule Appointment",
            "save_function": save_appointment,
            "state_key": "show_appointment_form",
            "form_data": {
                "patient_id": None,
                "doctor_id": None,
                "appointment_date": None,
                "appointment_time": None,
                "reason": None
            }
        },
        "prescription": {
            "title": "Add New Prescription",
            "submit_text": "Save Prescription",
            "save_function": save_prescription,
            "state_key": "show_prescription_form",
            "form_data": {
                "record_id": None,
                "medication": None,
                "dosage": None,
                "frequency": None,
                "duration": None,
                "notes": None
            }
        },
        "billing": {
            "title": "Create New Bill",
            "submit_text": "Create Bill",
            "save_function": save_bill,
            "state_key": "show_billing_form",
            "form_data": {
                "patient_id": None,
                "record_id": None,
                "amount": None
            }
        },
        "medical_record": {
            "title": "Add New Medical Record",
            "submit_text": "Save Medical Record",
            "save_function": save_medical_record,
            "state_key": "show_medical_record_form",
            "form_data": {
                "patient_id": None,
                "doctor_id": None,
                "diagnosis": None,
                "treatment": None,
                "notes": None
            }
        }
    }
    
    # Get the configuration for the requested form type
    config = form_config[form_type]
    form_data = config["form_data"]
    
    # Function to close form and update page
    def close_form(_):
        # Remove the overlay
        page.overlay.clear()
        page.update()
    
    # Create form fields based on form_type
    form_fields = []
    
    # Common header row for all forms
    form_fields.append(
        Row(
            controls=[
                Text(config["title"], size=20, weight="bold"),
                IconButton(
                    icon=Icons.CLOSE,
                    on_click=close_form
                ),
            ],
            alignment="spaceBetween",
        )
    )
    
    # Create form-specific fields
    if form_type == "appointment":
        form_fields.extend([
            Dropdown(
                label="Select Patient",
                options=patient_options,
                on_change=lambda e: form_data.update({"patient_id": e.control.value}),
                width=500,
            ),
            Dropdown(
                label="Select Doctor",
                options=doctor_options,
                on_change=lambda e: form_data.update({"doctor_id": e.control.value}),
                width=500,
            ),
            ElevatedButton(
                "Pick date",
                icon=Icons.CALENDAR_MONTH,
                on_click=lambda e: page.open(
                    DatePicker(
                        first_date=datetime(year=2024, month=3, day=10),
                        last_date=datetime(year=2040, month=12, day=31),
                        date_picker_mode=DatePickerMode.DAY,
                        on_change=lambda e: form_data.update({"appointment_date": e.control.value.strftime("%Y-%m-%d")}),
                    ),
                ),
            ),
            ElevatedButton(
                "Pick time",
                icon=Icons.TIME_TO_LEAVE,
                on_click=lambda _: page.open(
                    TimePicker(
                        confirm_text="Confirm",
                        error_invalid_text="Time out of range",
                        help_text="Pick your time slot",                
                        on_change=lambda e: form_data.update({"appointment_time": e.control.value.strftime("%H:%M")}),
                    )
                ),
            )
            ,
            TextField(
                label="Reason",
                multiline=True,
                min_lines=3,
                on_change=lambda e: form_data.update({"reason": e.control.value}),
                width=500,
            )
        ])
    
    elif form_type == "prescription":
        # Create empty records dropdown initially
        records_dropdown = Dropdown(
            label="Select Medical Record",
            options=[],
            on_change=lambda e: form_data.update({"record_id": e.control.value}),
            width=500,
            disabled=True,
        )
        
        # Function to update records when patient is selected
        def update_records(e):
            patient_id = e.control.value
            if patient_id:
                records = db.get_patient_records(int(patient_id))
                record_options = [
                    dropdown.Option(
                        key=str(r["id"]), 
                        text=f"{r['diagnosis']} ({r['record_date']})"
                    ) for r in records
                ]
                records_dropdown.options = record_options
                records_dropdown.disabled = False
                records_dropdown.update()
                page.update()
        
        form_fields.extend([
            Dropdown(
                label="Select Patient",
                options=patient_options,
                on_change=update_records,
                width=500,
            ),
            records_dropdown,
            TextField(
                label="Medication",
                on_change=lambda e: form_data.update({"medication": e.control.value}),
                width=500,
            ),
            TextField(
                label="Dosage (e.g., 10mg)",
                on_change=lambda e: form_data.update({"dosage": e.control.value}),
                width=500,
            ),
            TextField(
                label="Frequency (e.g., Once daily)",
                on_change=lambda e: form_data.update({"frequency": e.control.value}),
                width=500,
            ),
            TextField(
                label="Duration (e.g., 3 months)",
                on_change=lambda e: form_data.update({"duration": e.control.value}),
                width=500,
            ),
            TextField(
                label="Notes",
                multiline=True,
                min_lines=3,
                on_change=lambda e: form_data.update({"notes": e.control.value}),
                width=500,
            )
        ])
    
    elif form_type == "billing":
        # Create empty records dropdown initially
        records_dropdown = Dropdown(
            label="Medical Record (Optional)",
            options=[],
            on_change=lambda e: form_data.update({"record_id": e.control.value}),
            width=500,
            disabled=True,
        )
        
        # Function to update records when patient is selected
        def update_records(e):
            patient_id = e.control.value
            form_data.update({"patient_id": patient_id})
            if patient_id:
                records = db.get_patient_records(int(patient_id))
                record_options = [
                    dropdown.Option(
                        key=str(r["id"]), 
                        text=f"{r['diagnosis']} ({r['record_date']})"
                    ) for r in records
                ]
                records_dropdown.options = record_options
                records_dropdown.disabled = False
                records_dropdown.update()
                page.update()
        
        form_fields.extend([
            Dropdown(
                label="Select Patient",
                options=patient_options,
                on_change=update_records,
                width=500,
            ),
            records_dropdown,
            TextField(
                label="Amount ($)",
                keyboard_type=KeyboardType.NUMBER,
                on_change=lambda e: form_data.update({"amount": float(e.control.value) if e.control.value else None}),
                width=500,
            )
        ])
    
    elif form_type == "medical_record":
        form_fields.extend([
            Dropdown(
                label="Select Patient",
                options=patient_options,
                on_change=lambda e: form_data.update({"patient_id": e.control.value}),
                width=500,
            ),
            Dropdown(
                label="Select Doctor",
                options=doctor_options,
                on_change=lambda e: form_data.update({"doctor_id": e.control.value}),
                width=500,
            ),
            TextField(
                label="Diagnosis",
                on_change=lambda e: form_data.update({"diagnosis": e.control.value}),
                width=500,
            ),
            TextField(
                label="Treatment",
                on_change=lambda e: form_data.update({"treatment": e.control.value}),
                width=500,
            ),
            TextField(
                label="Notes",
                multiline=True,
                min_lines=3,
                on_change=lambda e: form_data.update({"notes": e.control.value}),
                width=500,
            )
        ])
    
    # Add submit/cancel buttons for all forms
    form_fields.append(
        Row(
            controls=[
                ElevatedButton(
                    text=config["submit_text"],
                    on_click=lambda _: config["save_function"](form_data, page),
                    style=ButtonStyle(color=Colors.WHITE, bgcolor=Colors.BLUE_700),
                ),
                OutlinedButton(
                    text="Cancel",
                    on_click=close_form,
                ),
            ],
            alignment="end",
        )
    )
    
    # Create modal overlay using Container as a backdrop
    form_overlay = Container(
        content=Container(
            content=Column(
                controls=form_fields,
                spacing=20,
                scroll=ScrollMode.ADAPTIVE
            ),
            width=550,
            padding=padding.all(30),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(
                top_left=10,
                bottom_left=10,
                top_right=10,
                bottom_right=10,
            ),
            border=border.all(1, Colors.GREY_300),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=Colors.with_opacity(0.2, Colors.BLACK),
            ),
        ),
        alignment=alignment.center,
        padding=padding.all(20),
        bgcolor=Colors.with_opacity(0.5, Colors.BLACK),
    )
    
    return form_overlay

def save_appointment(form_data, page:Page):
    """Save new appointment to database"""
    try:
        db = HospitalDB()
        patient_id = int(form_data.get("patient_id"))
        doctor_id = int(form_data.get("doctor_id"))
        appointment_date = form_data.get("appointment_date")
        appointment_time = form_data.get("appointment_time")
        reason = form_data.get("reason")
        
        # Validate required fields
        if not all([patient_id, doctor_id, appointment_date, appointment_time]):
            # Show error alert
            print("Error", [patient_id, doctor_id, appointment_date, appointment_time])
            return
        
        # Add appointment to database
        appointment_id = db.add_appointment(
            patient_id, 
            doctor_id,
            appointment_date,
            appointment_time,
            reason
        )
        
        if appointment_id:
            # Close form and refresh dashboard
            page.overlay.pop()
            page.overlay.clear()
            page.update()
            page.overlay.append(
                Container(
                    content=Text("Appointment saved successfully!", color=Colors.WHITE),
                    padding=padding.all(10),
                    bgcolor=Colors.GREEN_600,
                    border_radius=BorderRadius(
                        top_left=8, top_right=8,
                        bottom_left=8, bottom_right=8
                    ),
                    height=50,
                    alignment=alignment.center,
                )
            )
            page.update()
            time.sleep(2)
            page.overlay.pop()
            page.update()
            # Here you should refresh the dashboard data
    except Exception as e:
        print(f"Error saving appointment: {e}")

def save_prescription(form_data, page):
    """Save new prescription to database"""
    try:
        db = HospitalDB()
        record_id = int(form_data.get("record_id"))
        medication = form_data.get("medication")
        dosage = form_data.get("dosage")
        frequency = form_data.get("frequency")
        duration = form_data.get("duration")
        notes = form_data.get("notes")
        
        # Validate required fields
        if not all([record_id, medication]):
            # Show error alert
            return
        
        # Add prescription to database
        prescription_id = db.add_prescription(
            record_id,
            medication,
            dosage,
            frequency,
            duration,
            notes
        )
        
        if prescription_id:
            # Close form and refresh dashboard
            print(len(page.overlay))
            page.overlay.pop()
            page.update()
            page.overlay.append(
                Container(
                    content=Text("Prescription saved successfully!", color=Colors.WHITE),
                    padding=padding.all(10),
                    bgcolor=Colors.GREEN_600,
                    border_radius=BorderRadius(
                        top_left=8, top_right=8,
                        bottom_left=8, bottom_right=8
                    ),
                    height=50,
                    alignment=alignment.bottom_right,
                )
            )
            page.update()
            time.sleep(2)
            page.overlay.pop()
            page.update()
            # Here you should refresh the dashboard data
    except Exception as e:
        print(f"Error saving prescription: {e}")

def save_bill(form_data, page):
    """Save new bill to database"""
    try:
        db = HospitalDB()
        patient_id = int(form_data.get("patient_id"))
        record_id = form_data.get("record_id")
        if record_id:
            record_id = int(record_id)
        amount = form_data.get("amount")
        
        # Validate required fields
        if not all([patient_id, amount]):
            # Show error alert
            return
        
        # Add bill to database
        bill_id = db.add_bill(
            patient_id,
            amount,
            record_id
        )
        
        if bill_id:
            # Close form and refresh dashboard
            page.overlay.pop()
            page.update()
            page.overlay.append(
                Container(
                    content=Text("Billing saved successfully!", color=Colors.WHITE),
                    padding=padding.all(10),
                    bgcolor=Colors.GREEN_600,
                    border_radius=BorderRadius(
                        top_left=8, top_right=8,
                        bottom_left=8, bottom_right=8
                    ),
                    height=50,
                    alignment=alignment.bottom_right,
                )
            )
            page.update()
            time.sleep(2)
            page.overlay.pop()
            page.update()
            # Here you should refresh the dashboard data
    except Exception as e:
        print(f"Error saving bill: {e}")

def save_medical_record(form_data, page):
    """Save new medical record to database"""
    try:
        db = HospitalDB()
        patient_id = int(form_data.get("patient_id"))
        doctor_id = int(form_data.get("doctor_id"))
        diagnosis = form_data.get("diagnosis")
        treatment = form_data.get("treatment")
        notes = form_data.get("notes")
        
        # Validate required fields
        if not all([patient_id, doctor_id, diagnosis, treatment]):
            # Show error alert
            return
        
        # Add medical record to database
        record_id = db.add_medical_record(
            patient_id, 
            doctor_id,
            diagnosis,
            treatment,
            notes
        )
        
        if record_id:
            # Close form and refresh dashboard
            page.overlay.pop()
            page.update()
            page.overlay.append(
                Container(
                    content=Text("Medical Record saved successfully!", color=Colors.WHITE),
                    padding=padding.all(10),
                    bgcolor=Colors.GREEN_600,
                    border_radius=BorderRadius(
                        top_left=8, top_right=8,
                        bottom_left=8, bottom_right=8
                    ),
                    height=50,
                    alignment=alignment.bottom_right,
                )
            )
            page.update()
            time.sleep(2)
            page.overlay.pop()
            page.update()
            # Here you should refresh the dashboard data
    except Exception as e:
        print(f"Error saving medical record: {e}")

def patient_details(patient_id: int):
    db = HospitalDB()
    patient_data = db.get_patient(patient_id)
    if not patient_data:
        return Text("Patient not found", color=Colors.RED)

    medical_records = db.get_patient_records(patient_id)
    prescriptions = db.get_patient_prescriptions(patient_id)
    bills = db.get_patient_bills(patient_id)

    # Blue color palette
    PRIMARY_BLUE = "#1976D2"
    LIGHT_BLUE = "#64B5F6"
    VERY_LIGHT_BLUE = "#E3F2FD"
    DARK_BLUE = "#0D47A1"
    ACCENT_BLUE = "#2196F3"

    def profile_header():
        return Container(
            content=Row(
                controls=[
                    Container(
                        content=CircleAvatar(
                            content=Text(
                                patient_data.get("name", "")[0].upper(),
                                size=24,
                                color=Colors.WHITE,
                                weight=FontWeight.BOLD,
                            ),
                            bgcolor=PRIMARY_BLUE,
                            radius=40,
                        ),
                        margin=margin.only(right=15),
                    ),
                    Column(
                        controls=[
                            Text(
                                patient_data.get("name", "").title(),
                                weight=FontWeight.BOLD,
                                size=24,
                                color=DARK_BLUE,
                            ),
                            Text(
                                f"{dob_to_age(patient_data.get('date_of_birth', ''))} yrs • {patient_data.get('gender', '')} • {patient_data.get('blood_group', '')}ve",
                                size=16,
                                color=Colors.GREY_700,
                            ),
                            Container(
                                content=Text(
                                    "Active Patient",
                                    color=Colors.WHITE,
                                    size=12,
                                    weight=FontWeight.W_500,
                                ),
                                padding=padding.only(left=10, right=10, top=4, bottom=4),
                                border_radius=BorderRadius(12, 12, 12, 12),
                                bgcolor=PRIMARY_BLUE,
                                margin=margin.only(top=5),
                            ),
                        ],
                        spacing=3,
                        horizontal_alignment=CrossAxisAlignment.START,
                    ),
                ],
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            padding=padding.all(20),
            border_radius=BorderRadius(0, 0, 15, 15),
            bgcolor=VERY_LIGHT_BLUE,
            margin=margin.only(bottom=20),
        )

    def contact_info_card():
        return Container(
            content=Column(
                controls=[
                    Text(
                        "Contact Information",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=DARK_BLUE,
                    ),
                    Divider(height=1, color=Colors.BLACK12),
                    ListTile(
                        leading=Icon(Icons.PHONE, color=PRIMARY_BLUE),
                        title=Text("Phone"),
                        subtitle=Text(patient_data.get("phone", "")),
                    ),
                    ListTile(
                        leading=Icon(Icons.EMAIL, color=PRIMARY_BLUE),
                        title=Text("Email"),
                        subtitle=Text(patient_data.get("email", "")),
                    ),
                    ListTile(
                        leading=Icon(Icons.HOME, color=PRIMARY_BLUE),
                        title=Text("Address"),
                        subtitle=Text(patient_data.get("address", "")),
                    ),
                    ListTile(
                        leading=Icon(Icons.CALENDAR_TODAY, color=PRIMARY_BLUE),
                        title=Text("Next Appointment"),
                        subtitle=Text(patient_data.get("next_appointment", "")),
                    ),
                ],
                spacing=5,
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(10, 10, 10, 10),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            margin=margin.only(bottom=20),
        )

    def record_card(record):
        return Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(Icons.MEDICAL_SERVICES, color=PRIMARY_BLUE, size=20),
                            Text(
                                f"Diagnosis: {record['diagnosis']}",
                                size=16,
                                weight=FontWeight.BOLD,
                                color=DARK_BLUE,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Container(
                        content=Column(
                            controls=[
                                Text(f"Treatment: {record['treatment']}", size=14),
                                Text(f"Notes: {record['notes']}", size=14),
                                Container(
                                    content=Text(
                                        f"{record['record_date']}",
                                        size=12,
                                        color=Colors.WHITE,
                                    ),
                                    padding=padding.only(left=8, right=8, top=3, bottom=3),
                                    border_radius=BorderRadius(10, 10, 10, 10),
                                    bgcolor=LIGHT_BLUE,
                                    alignment=alignment.center_right,
                                ),
                            ],
                            spacing=8,
                            alignment=MainAxisAlignment.START,
                        ),
                        padding=padding.only(left=30),
                    ),
                ],
                spacing=10,
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(10, 10, 10, 10),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            margin=margin.only(bottom=10),
            border=Border(
                left=BorderSide(3, PRIMARY_BLUE),
            ),
        )

    def prescription_card(prescription):
        return Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(Icons.MEDICATION, color=PRIMARY_BLUE, size=20),
                            Text(
                                f"{prescription['medication']}",
                                size=16,
                                weight=FontWeight.BOLD,
                                color=DARK_BLUE,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Container(
                        content=Column(
                            controls=[
                                Text(f"Dosage: {prescription['dosage']}", size=14),
                                Text(f"Frequency: {prescription['frequency']}", size=14),
                                Text(f"Duration: {prescription['duration']}", size=14),
                                Text(f"Notes: {prescription['notes']}", size=12, color=Colors.GREY_600),
                            ],
                            spacing=5,
                            alignment=MainAxisAlignment.START,
                        ),
                        padding=padding.only(left=30),
                    ),
                ],
                spacing=10,
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(10, 10, 10, 10),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            margin=margin.only(bottom=10),
            border=Border(
                left=BorderSide(3, ACCENT_BLUE),
            ),
        )

    def bill_card(bill):
        payment_status = bill['payment_status']
        status_color = PRIMARY_BLUE if payment_status.lower() == "paid" else Colors.ORANGE_500
        
        return Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Container(
                                content=Icon(Icons.RECEIPT, color=Colors.WHITE, size=20),
                                padding=padding.all(8),
                                bgcolor=PRIMARY_BLUE,
                                border_radius=BorderRadius(10, 10, 10, 10),
                            ),
                            Column(
                                controls=[
                                    Text(f"${bill['amount']}", size=18, weight=FontWeight.BOLD),
                                    Container(
                                        content=Text(
                                            f"{payment_status}",
                                            size=12,
                                            color=Colors.WHITE,
                                            weight=FontWeight.W_500,
                                        ),
                                        padding=padding.only(left=10, right=10, top=3, bottom=3),
                                        border_radius=BorderRadius(10, 10, 10, 10),
                                        bgcolor=status_color,
                                    ),
                                ],
                                spacing=5,
                            ),
                            Column(
                                controls=[
                                    Text(f"Date: {bill['payment_date']}", size=14),
                                    Text(f"Method: {bill['payment_method']}", size=14),
                                ],
                                spacing=5,
                                horizontal_alignment=CrossAxisAlignment.END,
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(10, 10, 10, 10),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            margin=margin.only(bottom=10),
        )

    def section_header(title, icon):
        return Container(
            content=Row(
                controls=[
                    Icon(icon, color=PRIMARY_BLUE, size=24),
                    Text(
                        title,
                        size=20,
                        weight=FontWeight.BOLD,
                        color=DARK_BLUE,
                    ),
                ],
                spacing=10,
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            margin=margin.only(top=10, bottom=15),
        )

    return Container(
        content=Column(
            controls=[
                profile_header(),
                Tabs(
                    tabs=[
                        Tab(
                            text="Overview",
                            icon=Icons.DASHBOARD,
                            content=Container(
                                content=Column(
                                    controls=[
                                        contact_info_card(),
                                        section_header("Recent Medical Record", Icons.MEDICAL_SERVICES),
                                        record_card(medical_records[0] if medical_records else {"diagnosis": "No records", "treatment": "N/A", "notes": "N/A", "record_date": "N/A"}),
                                        section_header("Current Prescriptions", Icons.MEDICATION),
                                        prescription_card(prescriptions[0] if prescriptions else {"medication": "No prescriptions", "dosage": "N/A", "frequency": "N/A", "duration": "N/A", "notes": "N/A"}),
                                        section_header("Recent Bill", Icons.RECEIPT),
                                        bill_card(bills[0] if bills else {"amount": "0", "payment_status": "N/A", "payment_date": "N/A", "payment_method": "N/A"}),
                                    ],
                                    scroll=ScrollMode.ADAPTIVE,
                                ),
                                padding=padding.only(left=20, right=20, top=20, bottom=20),
                            ),
                        ),
                        Tab(
                            text="Medical Records",
                            icon=Icons.ASSIGNMENT,
                            content=Container(
                                content=Column(
                                    controls=[
                                        section_header("Medical Records", Icons.MEDICAL_SERVICES),
                                        Column(
                                            controls=[record_card(record) for record in medical_records],
                                            spacing=10,
                                        ) if medical_records else Text("No medical records available"),
                                    ],
                                    scroll=ScrollMode.ADAPTIVE,
                                ),
                                padding=padding.only(left=20, right=20, top=20, bottom=20),
                            ),
                        ),
                        Tab(
                            text="Prescriptions",
                            icon=Icons.MEDICATION,
                            content=Container(
                                content=Column(
                                    controls=[
                                        section_header("Prescriptions", Icons.MEDICATION),
                                        Column(
                                            controls=[prescription_card(prescription) for prescription in prescriptions],
                                            spacing=10,
                                        ) if prescriptions else Text("No prescriptions available"),
                                    ],
                                    scroll=ScrollMode.ADAPTIVE,
                                ),
                                padding=padding.only(left=20, right=20, top=20, bottom=20),
                            ),
                        ),
                        Tab(
                            text="Billing",
                            icon=Icons.RECEIPT,
                            content=Container(
                                content=Column(
                                    controls=[
                                        section_header("Billing History", Icons.RECEIPT),
                                        Column(
                                            controls=[bill_card(bill) for bill in bills],
                                            spacing=10,
                                        ) if bills else Text("No billing information available"),
                                    ],
                                    scroll=ScrollMode.ADAPTIVE,
                                ),
                                padding=padding.only(left=20, right=20, top=20, bottom=20),
                            ),
                        ),
                    ],
                    selected_index=0,
                    animation_duration=300,
                ),
            ],
            spacing=0,
            scroll=ScrollMode.ADAPTIVE,
        ),
        padding=0,
        bgcolor=Colors.WHITE,
        expand=True,
    )

def dob_to_age(dob: str) -> str:
    # dob format = yyyy-mm-dd
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return str(age)

def add_patient_form(db: HospitalDB, page: Page, on_add_complete):
    """
    Create a form for adding a new patient to the database.
    
    Args:
        db: The hospital database instance
        page: The current page
        on_add_complete: Callback function to execute when a patient is successfully added
    """
    # Form fields
    name_field = TextField(
        label="Full Name*",
        border_radius=8,
        text_size=14,
        expand=True,
    )
    
    email_field = TextField(
        label="Email",
        border_radius=8,
        text_size=14,
        expand=True,
        keyboard_type=KeyboardType.EMAIL,
    )
    
    phone_field = TextField(
        label="Phone Number",
        border_radius=8,
        text_size=14,
        expand=True,
        keyboard_type=KeyboardType.PHONE,
    )
    
    address_field = TextField(
        label="Address",
        border_radius=8,
        text_size=14,
        expand=True,
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    
    dob_field = TextField(
        label="Date of Birth (YYYY-MM-DD)",
        border_radius=8,
        text_size=14,
        expand=True,
        hint_text="e.g., 1990-01-15",
    )
    
    # Gender dropdown
    gender_dropdown = Dropdown(
        options=[
            dropdown.Option("Male"),
            dropdown.Option("Female"),
            dropdown.Option("Other"),
        ],
        label="Gender",
        border_radius=8,
        text_size=14,
        expand=True,
    )
    
    # Blood group dropdown
    blood_group_dropdown = Dropdown(
        options=[
            dropdown.Option("A+"),
            dropdown.Option("A-"),
            dropdown.Option("B+"),
            dropdown.Option("B-"),
            dropdown.Option("AB+"),
            dropdown.Option("AB-"),
            dropdown.Option("O+"),
            dropdown.Option("O-"),
        ],
        label="Blood Group",
        border_radius=8,
        text_size=14,
        expand=True,
    )
    
    # Error text to display validation errors
    error_text = Text("", color=Colors.RED_500, size=14)
    
    def validate_form():
        """Validate the form fields"""
        if not name_field.value:
            error_text.value = "Patient name is required"
            page.update()
            return False
            
        # Validate date format if provided
        if dob_field.value:
            try:
                datetime.strptime(dob_field.value, "%Y-%m-%d")
            except ValueError:
                error_text.value = "Date of birth must be in YYYY-MM-DD format"
                page.update()
                return False
                
        return True
    
    def save_patient(e):
        """Save the patient to the database"""
        if not validate_form():
            return
            
        try:
            # Add the patient to the database
            patient_id = db.add_patient(
                name=name_field.value,
                email=email_field.value if email_field.value else None,
                phone=phone_field.value if phone_field.value else None,
                address=address_field.value if address_field.value else None,
                date_of_birth=dob_field.value if dob_field.value else None,
                gender=gender_dropdown.value if gender_dropdown.value else None,
                blood_group=blood_group_dropdown.value if blood_group_dropdown.value else None
            )
            
            if patient_id:
                # Show success message
                page.show_snack_bar(SnackBar(
                    Text(f"Patient {name_field.value} added successfully", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_600
                ))
                
                # Call the completion callback
                on_add_complete()
            else:
                # Show error message
                error_text.value = "Failed to add patient. Please try again."
                page.update()
                
        except Exception as ex:
            error_text.value = f"Error: {str(ex)}"
            page.update()
    
    def cancel_form(e):
        """Cancel the form and close the overlay"""
        page.overlay.pop()
        page.update()
    
    # Create the form layout
    form_content = Column(
        controls=[
            # Form title already included in the overlay container
            
            # Required fields section
            Container(
                content=Column(
                    controls=[
                        Text("Basic Information", weight=FontWeight.BOLD, size=16),
                        name_field,
                        Row(
                            controls=[
                                dob_field,
                                gender_dropdown,
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=15,
                ),
                padding=padding.all(10),
            ),
            
            # Optional information section
            Container(
                content=Column(
                    controls=[
                        Text("Contact Information", weight=FontWeight.BOLD, size=16),
                        Row(
                            controls=[
                                phone_field,
                                email_field,
                            ],
                            spacing=10,
                        ),
                        address_field,
                    ],
                    spacing=15,
                ),
                padding=padding.all(10),
            ),
            
            # Medical information section
            Container(
                content=Column(
                    controls=[
                        Text("Medical Information", weight=FontWeight.BOLD, size=16),
                        blood_group_dropdown,
                    ],
                    spacing=15,
                ),
                padding=padding.all(10),
            ),
            
            # Error message
            Container(
                content=error_text,
                padding=padding.only(left=10, right=10),
            ),
            
            # Form buttons
            Container(
                content=Row(
                    controls=[
                        ElevatedButton(
                            content=Text("Cancel"),
                            style=ButtonStyle(
                                shape=RoundedRectangleBorder(radius=8),
                                color=Colors.BLACK,
                                bgcolor=Colors.WHITE,
                            ),
                            on_click=cancel_form,
                        ),
                        ElevatedButton(
                            content=Text("Save Patient"),
                            style=ButtonStyle(
                                shape=RoundedRectangleBorder(radius=8),
                                color=Colors.WHITE,
                                bgcolor=Colors.BLUE,
                            ),
                            on_click=save_patient,
                        ),
                    ],
                    spacing=10,
                    alignment=MainAxisAlignment.END,
                ),
                padding=padding.all(10),
            ),
        ],
        spacing=10,
        scroll=ScrollMode.ALWAYS,
        expand=True
    )
    
    return form_content

def patients(db: HospitalDB, page: Page) -> Container:
    patient_list = db.get_all_patients()
    patient_controls = []

    def close_patient_details(e):
        page.overlay.pop()
        page.update()

    def show_patient_details(patient_id):
        patient_detail_content = patient_details(patient_id)
        
        overlay_container = Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Text("Patient Details", size=24, weight=FontWeight.BOLD),
                            IconButton(
                                icon=Icons.CLOSE,
                                on_click=close_patient_details,
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    Divider(height=1, color=Colors.BLACK12),
                    patient_detail_content,
                ],
                spacing=20,
            ),
            padding=padding.all(20),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(
                top_left=10,
                top_right=10,
                bottom_left=10,
                bottom_right=10
            ),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            width=page.width - 100,
            height=page.height - 100,
            alignment=alignment.center,
            margin=margin.only(top=40, left=60)
        )
    
        page.overlay.append(overlay_container)
        page.update()
    
    def search_patients(e):
        search_term = search_field.value.lower()
        filtered_patients = [p for p in db.get_all_patients() if search_term in p.get("name", "").lower()]
        
        # Clear the existing patient controls
        patient_grid.controls.clear()
        
        # Add the filtered patients
        for patient in filtered_patients:
            patient_grid.controls.append(patient_card(patient))
        
        page.update()
    
    def open_add_patient_form(e):
        # This function would show a form to add a new patient
        add_patient_content = add_patient_form(db, page, on_add_complete)
        
        overlay_container = Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Text("Add New Patient", size=24, weight=FontWeight.BOLD),
                            IconButton(
                                icon=Icons.CLOSE,
                                on_click=close_patient_details,  # Reusing the same close function
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    Divider(height=1, color=Colors.BLACK12),
                    add_patient_content,
                ],
                spacing=20,
            ),
            padding=padding.all(20),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(
                top_left=10,
                top_right=10,
                bottom_left=10,
                bottom_right=10
            ),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            width=page.width - 100,
            height=page.height - 100,
            alignment=alignment.center,
            margin=margin.only(top=40, left=60)
        )
    
        page.overlay.append(overlay_container)
        page.update()
    
    def on_add_complete():
        # Refresh the patient list
        patient_list = db.get_all_patients()
        patient_grid.controls.clear()
        
        for patient in patient_list:
            patient_grid.controls.append(patient_card(patient))
        
        page.overlay.pop()
        page.update()
    
    def patient_card(patient_data):
        condition_chips = Row(spacing=5)
        if patient_data.get("conditions"):
            for condition in patient_data["conditions"]:
                condition_chips.controls.append(
                    Container(
                        content=Text(condition, size=12),
                        padding=padding.only(left=10, right=10, top=5, bottom=5),
                        bgcolor=Colors.BLACK12,
                        border_radius=BorderRadius(20, 20, 20, 20),
                    )
                )

        card = Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Row(
                                controls=[
                                    Container(
                                        content=Icon(Icons.PERSON, size=24, color=Colors.BLUE),
                                        width=40,
                                        height=40,
                                        bgcolor=Colors.BLUE_50,
                                        border_radius=BorderRadius(20, 20, 20, 20),
                                        alignment=alignment.center,
                                    ),
                                    Column(
                                        controls=[
                                            Text(patient_data.get("name", ""), weight=FontWeight.BOLD, size=16),
                                            Text(f"{dob_to_age(patient_data.get('date_of_birth', ''))} yrs • {patient_data.get('gender', '')}", 
                                                size=12, color=Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ],
                                alignment=MainAxisAlignment.START,
                            ),
                            Container(
                                content=Text(patient_data.get("status", "").capitalize(), color=Colors.WHITE, size=12),
                                padding=padding.only(left=10, right=10, top=3, bottom=3),
                                bgcolor=Colors.BLUE if patient_data.get("status").lower() == "active" else Colors.GREY_500,
                                border_radius=BorderRadius(20, 20, 20, 20),
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    Divider(height=1, color=Colors.BLACK12),
                    Row(
                        controls=[
                            Icon(Icons.PHONE, size=16, color=Colors.GREY_600),
                            Text(patient_data.get("phone", ""), size=14),
                        ],
                        spacing=5,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Row(
                        controls=[
                            Icon(Icons.CALENDAR_TODAY, size=16, color=Colors.GREY_600),
                            Text(f"Next Appointment: {patient_data.get('next_appointment', '')}", size=14),
                        ],
                        spacing=5,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    condition_chips,
                    Row(
                        controls=[
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(Icons.ARTICLE_OUTLINED, size=16),
                                        Text("View Details", size=14),
                                    ],
                                    spacing=5,
                                    alignment=MainAxisAlignment.CENTER,
                                ),
                                padding=padding.only(top=10, bottom=10),
                                border=Border(
                                    left=BorderSide(1, Colors.BLACK12),
                                    right=BorderSide(1, Colors.BLACK12),
                                    top=BorderSide(1, Colors.BLACK12),
                                    bottom=BorderSide(1, Colors.BLACK12),
                                ),
                                border_radius=BorderRadius(5, 5, 5, 5),
                                alignment=alignment.center,
                                expand=True,
                                on_click=lambda e: show_patient_details(patient_data.get('id'))
                            ),
                            Container(
                                content=Icon(Icons.MORE_VERT, size=20),
                                padding=padding.only(left=10, right=10),
                                on_click=lambda e: print(f"More options for {patient_data.get('name')}")
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    )
                ],
                spacing=12,
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(8, 8, 8, 8),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            width=400,
            height=400
        )

        return card

    # Create the search field
    search_field = TextField(
        label="Search patients",
        prefix_icon=Icons.SEARCH,
        on_submit=search_patients,
        border_radius=8,
        expand=True,
        hint_text="Search by name",
    )
    
    # Create the add patient button
    add_button = ElevatedButton(
        content=Row(
            controls=[
                Icon(Icons.ADD),
                Text("Add Patient"),
            ],
            spacing=5,
        ),
        style=ButtonStyle(
            shape=RoundedRectangleBorder(radius=8),
            color=Colors.WHITE,
            bgcolor=Colors.BLUE,
        ),
        on_click=open_add_patient_form,
    )
    
    # Create the patient grid
    patient_grid = GridView(
        controls=[patient_card(patient) for patient in patient_list],
        expand=1,
        runs_count=3,
        spacing=7,
        run_spacing=10,
        child_aspect_ratio=1.3
    )

    for patient in patient_list:
        patient_controls.append(
            patient_card(patient)
        )

    return Container(
        Column(
            controls=[
                Text("Patients", color=Colors.BLACK87, size=24),
                # Add search and button row below the title
                Row(
                    controls=[
                        search_field,
                        add_button,
                    ],
                    spacing=10,
                ),
                Container(
                    patient_grid
                )
            ],
            spacing=20,
        ),
        expand=True,
        padding=20
    )

def doctors_and_nurses(db: HospitalDB, page: Page) -> Container:
    doctor_list = db.get_all_users("doctor")
    doctor_list2 = db.get_all_users("Doctor")
    nurse_list = db.get_all_users("nurse")
    nurse_list2 = db.get_all_users("Noctor")
    
    # Combined list for searching
    all_users = doctor_list + nurse_list + doctor_list2 + nurse_list2
    displayed_users = all_users.copy()
    
    # Form field values
    name_value = TextField(label="Full Name", hint_text="Enter full name")
    email_value = TextField(label="Email", hint_text="Enter email address")
    password_value = TextField(label="Password", hint_text="Enter password", password=True)
    role_value = Dropdown(
        label="Role",
        options=[
            dropdown.Option("doctor"),
            dropdown.Option("nurse"),
        ],
    )
    specialization_value = TextField(label="Specialization", hint_text="e.g., Cardiology, Pediatrics")
    phone_value = TextField(label="Phone", hint_text="Enter phone number")
    address_value = TextField(label="Address", hint_text="Enter address", multiline=True, min_lines=2)
    
    def search_users(e):
        query = search_field.value.lower()
        if query:
            displayed_users.clear()
            for user in all_users:
                if (query in user.get("name", "").lower() or 
                    query in user.get("specialization", "").lower() or 
                    query in user.get("role", "").lower() or 
                    query in user.get("email", "").lower()):
                    displayed_users.append(user)
        else:
            displayed_users.clear()
            displayed_users.extend(all_users)
        
        # Update the grid view with filtered results
        grid_view.controls = [user_card(user, "Doctor" if user in doctor_list + doctor_list2 else "Nurse") for user in displayed_users]
        page.update()
    
    def show_add_dialog(e):
        # Clear form fields
        name_value.value = ""
        email_value.value = ""
        password_value.value = ""
        role_value.value = None
        specialization_value.value = ""
        phone_value.value = ""
        address_value.value = ""
        
        # Show dialog
        page.dialog = add_dialog
        add_dialog.open = True
        page.update()
    
    def close_dialog(e):
        add_dialog.open = False
        page.update()
    
    def handle_role_change(e):
        # Show/hide specialization field based on role
        if role_value.value.lower() == "doctor":
            specialization_container.visible = True
        else:
            specialization_container.visible = False
            specialization_value.value = ""
        page.update()
    
    def submit_form(e):
        try:
            # Validate form
            if not name_value.value or not email_value.value or not password_value.value or not role_value.value:
                page.show_snack_bar(SnackBar(Text("Please fill all required fields"), bgcolor=Colors.RED_500))
                return
            
            # Add user to database
            user_id = db.add_user(
                name=name_value.value,
                email=email_value.value,
                password=password_value.value,
                role=role_value.value,
                specialization=specialization_value.value if role_value.value == "Doctor" else None,
                phone=phone_value.value,
                address=address_value.value
            )
            
            if user_id:
                # Refresh the user list
                if role_value.value == "Doctor":
                    doctor_list.clear()
                    doctor_list.extend(db.get_all_users("Doctor"))
                else:
                    nurse_list.clear()
                    nurse_list.extend(db.get_all_users("Nurse"))
                
                all_users.clear()
                all_users.extend(doctor_list + nurse_list)
                displayed_users.clear()
                displayed_users.extend(all_users)
                
                # Update the grid view
                grid_view.controls = [user_card(user, "Doctor" if user in doctor_list else "Nurse") for user in displayed_users]
                
                # Close dialog and show success message
                add_dialog.open = False
                page.show_snack_bar(SnackBar(
                    Text(f"{role_value.value} added successfully"), 
                    bgcolor=Colors.GREEN_500
                ))
            else:
                page.show_snack_bar(SnackBar(
                    Text("Failed to add user. Email may already exist."), 
                    bgcolor=Colors.RED_500
                ))
                
        except Exception as ex:
            page.show_snack_bar(SnackBar(Text(f"Error: {str(ex)}"), bgcolor=Colors.RED_500))
        
        page.update()
    
    # Specialization container to show/hide based on role
    specialization_container = Container(
        content=specialization_value,
        visible=True
    )
    
    # Create add dialog
    add_dialog = AlertDialog(
        title=Text("Add Doctor/Nurse", size=20, weight=FontWeight.BOLD),
        content=Container(
            content=Column([
                name_value,
                email_value,
                password_value,
                role_value,
                specialization_container,
                phone_value,
                address_value,
            ], spacing=15, scroll=ScrollMode.AUTO),
            padding=padding.all(20),
            width=450,
            height=500,
        ),
        actions=[
            TextButton("Cancel", on_click=close_dialog),
            ElevatedButton(
                "Add",
                on_click=submit_form,
                bgcolor=Colors.BLUE,
                color=Colors.WHITE,
            ),
        ],
        actions_alignment=MainAxisAlignment.END,
        on_dismiss=close_dialog,
    )
    
    # Connect role dropdown to specialization visibility
    role_value.on_change = handle_role_change
    
    # Search field
    search_field = TextField(
        label="Search by name, specialization, role or email",
        prefix_icon=Icons.SEARCH,
        on_change=search_users,
        expand=True,
        border_color=Colors.BLUE,
    )
    
    # Add button
    add_button = ElevatedButton(
        content=Row(
            controls=[
                Icon(Icons.ADD),
                Text("Add Doctor/Nurse"),
            ],
            spacing=5,
        ),
        style=ButtonStyle(
            shape=RoundedRectangleBorder(radius=8),
            color=Colors.WHITE,
            bgcolor=Colors.BLUE,
        ),
        on_click=show_add_dialog,
    )

    def user_card(user_data, role):
        card = Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Row(
                                controls=[
                                    Container(
                                        content=Icon(Icons.PERSON, size=24, color=Colors.BLUE),
                                        width=40,
                                        height=40,
                                        bgcolor=Colors.BLUE_50,
                                        border_radius=BorderRadius(20, 20, 20, 20),
                                        alignment=alignment.center,
                                    ),
                                    Column(
                                        controls=[
                                            Text(user_data.get("name", ""), weight=FontWeight.BOLD, size=16),
                                            Text(user_data.get("specialization", "") if role.lower() == "doctor" else user_data.get("role", ""), size=12, color=Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ],
                                alignment=MainAxisAlignment.START,
                            ),
                            Container(
                                content=Text(user_data.get("status", "").capitalize(), color=Colors.WHITE, size=12),
                                padding=padding.only(left=10, right=10, top=3, bottom=3),
                                bgcolor=Colors.BLUE if user_data.get("status").lower() == "active" else Colors.GREY_500,
                                border_radius=BorderRadius(20, 20, 20, 20),
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    Divider(height=1, color=Colors.BLACK12),
                    Row(
                        controls=[
                            Icon(Icons.PHONE, size=16, color=Colors.GREY_600),
                            Text(user_data.get("phone", ""), size=14),
                        ],
                        spacing=5,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Row(
                        controls=[
                            Icon(Icons.EMAIL, size=16, color=Colors.GREY_600),
                            Text(user_data.get("email", ""), size=14),
                        ],
                        spacing=5,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Row(
                        controls=[
                            Icon(Icons.CALENDAR_TODAY, size=16, color=Colors.GREY_600),
                            Text(f"Date Joined: {user_data.get('date_joined', '')}", size=14),
                        ],
                        spacing=5,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
            ),
            padding=padding.all(15),
            bgcolor=Colors.WHITE,
            border_radius=BorderRadius(8, 8, 8, 8),
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
            width=400,
            height=200
        )

        return card

    # Initial user cards
    user_controls = [user_card(user, "Doctor" if user in doctor_list else "Nurse") for user in displayed_users]
    
    # Grid view with reference for updating
    grid_view = GridView(
        controls=user_controls,
        expand=1,
        runs_count=3,
        spacing=7,
        run_spacing=10,
        child_aspect_ratio=1.3
    )

    return Container(
        Column(
            controls=[
                Text("Doctors and Nurses", color=Colors.BLACK87, size=24, weight=FontWeight.BOLD),
                Row(
                    controls=[
                        search_field,
                        add_button,
                    ],
                    spacing=10,
                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                ),
                Container(
                    grid_view
                )
            ],
            spacing=20,
        ),
        padding=padding.all(20),
        expand=True,
    )

GEMINI_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)


def profile_page(page: Page, db: HospitalDB) -> Container:
    user = {}
    try:
        with open("user_session.txt", "r") as f:
            user["id"] = f.readline().replace("\n","")
            user["name"] = f.readline().replace("\n","")
            user["email"] = f.readline().replace("\n","")
            user["role"] = f.readline().replace("\n","")
    except:
        print("Error occurred")
    print(user)

    full_info = db.get_user(user_id=user["id"])
    full_info.pop("password")

    # Get doctor's patients
    patients = db.get_all_patients()
    doctor_patients = [p for p in patients if p['id'] in [r['patient_id'] for r in db.get_doctor_records(user["id"])]]

    # Get doctor's medical records
    medical_records = db.get_doctor_records(user["id"])

    # Get doctor's appointments
    appointments = db.get_appointments(doctor_id=user["id"])

    # Get doctor's prescriptions
    prescriptions = []
    for record in medical_records:
        prescriptions.extend(db.get_prescriptions(record["id"]))

    # Color scheme
    primary_color = "#3498db"  # Blue
    secondary_color = "#f8f9fa"  # Light gray
    accent_color = "#2ecc71"  # Green
    text_color = "#2c3e50"  # Dark blue-gray
    light_text = "#7f8c8d"  # Gray for secondary text
    
    # Doctor profile header
    profile_header = Container(
        content=Row(
            controls=[
                Container(
                    content=Icon(name=Icons.MEDICAL_SERVICES, size=60, color="#ffffff"),
                    width=100,
                    height=100,
                    bgcolor=primary_color,
                    border_radius=50,
                    alignment=alignment.center,
                ),
                Column(
                    controls=[
                        Text(f"Dr. {full_info['name']}", size=28, weight=FontWeight.BOLD, color=text_color),
                        Text(f"{full_info['specialization']}", size=18, color=light_text, italic=True),
                        Container(
                            content=Row(
                                controls=[
                                    Icon(name=Icons.EMAIL, color=primary_color, size=16),
                                    Text(f"{full_info['email']}", size=14, color=text_color),
                                ],
                                spacing=5,
                                alignment=MainAxisAlignment.START,
                            ),
                            margin=margin.only(top=5),
                        ),
                        Container(
                            content=Row(
                                controls=[
                                    Icon(name=Icons.PHONE, color=primary_color, size=16),
                                    Text(f"{full_info['phone']}", size=14, color=text_color),
                                ],
                                spacing=5,
                                alignment=MainAxisAlignment.START,
                            ),
                            margin=margin.only(top=5),
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=20,
            alignment=MainAxisAlignment.START,
        ),
        padding=10,
        bgcolor=secondary_color,
        border_radius=10,
        shadow=BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color=Colors.BLACK12,
            offset=Offset(0, 2),
        ),
        margin=margin.only(bottom=20),
    )
    
    # Stats overview
    stats_overview = Container(
        content=Row(
            controls=[
                Container(
                    content=Column(
                        controls=[
                            Text(str(len(doctor_patients)), size=24, weight=FontWeight.BOLD, color="#ffffff"),
                            Text("Patients", size=14, color="#ffffff"),
                        ],
                        spacing=5,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    padding=15,
                    bgcolor=primary_color,
                    border_radius=8,
                    expand=True,
                    alignment=alignment.center,
                ),
                Container(
                    content=Column(
                        controls=[
                            Text(str(len(medical_records)), size=24, weight=FontWeight.BOLD, color="#ffffff"),
                            Text("Records", size=14, color="#ffffff"),
                        ],
                        spacing=5,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    padding=15,
                    bgcolor="#9b59b6",  # Purple
                    border_radius=8,
                    expand=True,
                    alignment=alignment.center,
                ),
                Container(
                    content=Column(
                        controls=[
                            Text(str(len(appointments)), size=24, weight=FontWeight.BOLD, color="#ffffff"),
                            Text("Appointments", size=14, color="#ffffff"),
                        ],
                        spacing=5,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    padding=15,
                    bgcolor="#e74c3c",  # Red
                    border_radius=8,
                    expand=True,
                    alignment=alignment.center,
                ),
                Container(
                    content=Column(
                        controls=[
                            Text(str(len(prescriptions)), size=24, weight=FontWeight.BOLD, color="#ffffff"),
                            Text("Prescriptions", size=14, color="#ffffff"),
                        ],
                        spacing=5,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    padding=15,
                    bgcolor="#f39c12",  # Orange
                    border_radius=8,
                    expand=True,
                    alignment=alignment.center,
                ),
            ],
            spacing=10,
        ),
        margin=margin.only(bottom=20),
    )

    def patient_card(patient):
        return Container(
            content=Row(
                controls=[
                    Container(
                        content=Icon(name=Icons.PERSON, size=24, color="#ffffff"),
                        width=40,
                        height=40,
                        bgcolor=primary_color,
                        border_radius=20,
                        alignment=alignment.center,
                    ),
                    Column(
                        controls=[
                            Text(f"{patient['name']}", size=16, weight=FontWeight.BOLD, color=text_color),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.EMAIL, color=light_text, size=14),
                                        Text(f"{patient['email']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.PHONE, color=light_text, size=14),
                                        Text(f"{patient['phone']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    Column(
                        controls=[
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.CALENDAR_TODAY, color=light_text, size=14),
                                        Text(f"{patient['date_of_birth']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                            ),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.BLOODTYPE, color=light_text, size=14),
                                        Text(f"{patient['blood_group']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.WC, color=light_text, size=14),
                                        Text(f"{patient['gender']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                        ],
                        spacing=2,
                        width=150,
                    ),
                    IconButton(
                        icon=Icons.ARROW_FORWARD_IOS_ROUNDED,
                        icon_color=primary_color,
                        icon_size=16,
                        tooltip="View details",
                    ),
                ],
                spacing=10,
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            padding=15,
            bgcolor=Colors.WHITE,
            border_radius=8,
            shadow=BoxShadow(
                spread_radius=0,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 1),
            ),
            margin=margin.only(bottom=10),
        )

    def record_card(record):
        return Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(name=Icons.MEDICAL_INFORMATION, color=primary_color, size=20),
                            Text(f"{record['diagnosis']}", size=16, weight=FontWeight.BOLD, color=text_color),
                            Container(
                                content=Text(f"{record['record_date']}", size=12, color=light_text, italic=True),
                                padding=padding.symmetric(horizontal=8, vertical=4),
                                bgcolor=secondary_color,
                                border_radius=12,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Container(
                        content=Column(
                            controls=[
                                Row(
                                    controls=[
                                        Text("Treatment:", size=14, weight="w500", color=text_color),
                                        Text(f"{record['treatment']}", size=14, color=text_color),
                                    ],
                                    spacing=5,
                                ),
                                Container(
                                    content=Text(f"{record['notes']}", size=12, color=light_text),
                                    margin=margin.only(top=5),
                                ),
                            ],
                            spacing=5,
                        ),
                        margin=margin.only(top=10, left=30),
                    ),
                ],
                spacing=5,
            ),
            padding=15,
            bgcolor=Colors.WHITE,
            border_radius=8,
            shadow=BoxShadow(
                spread_radius=0,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 1),
            ),
            margin=margin.only(bottom=10),
        )

    def appointment_card(appointment):
        status_colors = {
            "Scheduled": "#3498db",  # Blue
            "Completed": "#2ecc71",  # Green
            "Cancelled": "#e74c3c",  # Red
            "Pending": "#f39c12",    # Orange
        }
        status_color = status_colors.get(appointment['status'], primary_color)
        
        return Container(
            content=Row(
                controls=[
                    Container(
                        content=Column(
                            controls=[
                                Text(appointment['appointment_date'].split("-")[2], size=20, weight=FontWeight.BOLD, color="#ffffff"),
                                Text(appointment['appointment_date'].split("-")[1], size=12, color="#ffffff"),
                            ],
                            spacing=0,
                            horizontal_alignment=CrossAxisAlignment.CENTER,
                        ),
                        width=50,
                        height=50,
                        bgcolor=primary_color,
                        border_radius=8,
                        alignment=alignment.center,
                        padding=5,
                    ),
                    Column(
                        controls=[
                            Text(f"{appointment['patient_name']}", size=16, weight=FontWeight.BOLD, color=text_color),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.ACCESS_TIME, color=light_text, size=14),
                                        Text(f"{appointment['appointment_time']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                            Container(
                                content=Row(
                                    controls=[
                                        Icon(name=Icons.DESCRIPTION, color=light_text, size=14),
                                        Text(f"{appointment['reason']}", size=12, color=light_text),
                                    ],
                                    spacing=5,
                                ),
                                margin=margin.only(top=2),
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    Container(
                        content=Text(appointment['status'], size=12, color="#ffffff"),
                        padding=padding.symmetric(horizontal=10, vertical=5),
                        bgcolor=status_color,
                        border_radius=15,
                        alignment=alignment.center,
                    ),
                ],
                spacing=15,
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            padding=15,
            bgcolor=Colors.WHITE,
            border_radius=8,
            shadow=BoxShadow(
                spread_radius=0,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 1),
            ),
            margin=margin.only(bottom=10),
        )

    def prescription_card(prescription):
        return Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(name=Icons.MEDICATION, color=primary_color, size=20),
                            Text(f"{prescription['medication']}", size=16, weight=FontWeight.BOLD, color=text_color),
                            Container(
                                content=Text(f"{prescription['dosage']}", size=12, weight=FontWeight.BOLD, color="#ffffff"),
                                padding=padding.symmetric(horizontal=8, vertical=4),
                                bgcolor=accent_color,
                                border_radius=12,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    Container(
                        content=Column(
                            controls=[
                                Container(
                                    content=Row(
                                        controls=[
                                            Container(
                                                content=Text("Frequency", size=12, color=light_text),
                                                padding=padding.symmetric(horizontal=8, vertical=4),
                                                bgcolor=secondary_color,
                                                border_radius=4,
                                                width=80,
                                            ),
                                            Text(f"{prescription['frequency']}", size=14, color=text_color),
                                        ],
                                        spacing=10,
                                        vertical_alignment=CrossAxisAlignment.CENTER,
                                    ),
                                    margin=margin.only(top=5),
                                ),
                                Container(
                                    content=Row(
                                        controls=[
                                            Container(
                                                content=Text("Duration", size=12, color=light_text),
                                                padding=padding.symmetric(horizontal=8, vertical=4),
                                                bgcolor=secondary_color,
                                                border_radius=4,
                                                width=80,
                                            ),
                                            Text(f"{prescription['duration']}", size=14, color=text_color),
                                        ],
                                        spacing=10,
                                        vertical_alignment=CrossAxisAlignment.CENTER,
                                    ),
                                    margin=margin.only(top=5),
                                ),
                                Container(
                                    content=Text(f"Notes: {prescription['notes']}", size=12, color=light_text),
                                    margin=margin.only(top=5),
                                ),
                            ],
                            spacing=2,
                        ),
                        margin=margin.only(top=10, left=30),
                    ),
                ],
                spacing=5,
            ),
            padding=15,
            bgcolor=Colors.WHITE,
            border_radius=8,
            shadow=BoxShadow(
                spread_radius=0,
                blur_radius=3,
                color=Colors.BLACK12,
                offset=Offset(0, 1),
            ),
            margin=margin.only(bottom=10),
        )

    # Patients tab content
    patients_content = Container(
        content=Column(
            controls=[
                Row(
                    controls=[
                        Container(
                            content=TextField(
                                hint_text="Search patients...",
                                prefix_icon=Icons.SEARCH,
                                border_radius=8,
                                filled=True,
                                bgcolor=secondary_color,
                            ),
                            expand=True,
                        ),
                        IconButton(
                            icon=Icons.ADD_ROUNDED,
                            bgcolor=primary_color,
                            icon_color=Colors.WHITE,
                            icon_size=20,
                            tooltip="Add new patient",
                        ),
                    ],
                    spacing=10,
                ),
                Divider(height=1, color=Colors.BLACK12),
                Column(
                    controls=[patient_card(p) for p in doctor_patients],
                    spacing=10,
                ),
            ],
            spacing=15,
            scroll=ScrollMode.ADAPTIVE,
            expand=True
        ),
        padding=15,
    )

    # Records tab content
    records_content = Container(
        content=Column(
            controls=[
                Row(
                    controls=[
                        Container(
                            content=TextField(
                                hint_text="Search records...",
                                prefix_icon=Icons.SEARCH,
                                border_radius=8,
                                filled=True,
                                bgcolor=secondary_color,
                            ),
                            expand=True,
                        ),
                        IconButton(
                            icon=Icons.ADD_ROUNDED,
                            bgcolor=primary_color,
                            icon_color=Colors.WHITE,
                            icon_size=20,
                            tooltip="Add new record",
                        ),
                    ],
                    spacing=10,
                ),
                Divider(height=1, color=Colors.BLACK12),
                Column(
                    controls=[record_card(r) for r in medical_records],
                    spacing=10,
                ),
            ],
            spacing=15,
            scroll=ScrollMode.ADAPTIVE,
            expand=True
        ),
        padding=15,
    )

    # Appointments tab content
    appointments_content = Container(
        content=Column(
            controls=[
                Row(
                    controls=[
                        Container(
                            content=TextField(
                                hint_text="Search appointments...",
                                prefix_icon=Icons.SEARCH,
                                border_radius=8,
                                filled=True,
                                bgcolor=secondary_color,
                            ),
                            expand=True,
                        ),
                        IconButton(
                            icon=Icons.ADD_ROUNDED,
                            bgcolor=primary_color,
                            icon_color=Colors.WHITE,
                            icon_size=20,
                            tooltip="Add new appointment",
                        ),
                    ],
                    spacing=10,
                ),
                Divider(height=1, color=Colors.BLACK12),
                Column(
                    controls=[appointment_card(a) for a in appointments],
                    spacing=10,
                    scroll=ScrollMode.ADAPTIVE,
                ),
            ],
            spacing=15,
            scroll=ScrollMode.ADAPTIVE,
            expand=True
        ),
        padding=15,
    )

    # Prescriptions tab content
    prescriptions_content = Container(
        content=Column(
            controls=[
                Row(
                    controls=[
                        Container(
                            content=TextField(
                                hint_text="Search prescriptions...",
                                prefix_icon=Icons.SEARCH,
                                border_radius=8,
                                filled=True,
                                bgcolor=secondary_color,
                            ),
                            expand=True,
                        ),
                        IconButton(
                            icon=Icons.ADD_ROUNDED,
                            bgcolor=primary_color,
                            icon_color=Colors.WHITE,
                            icon_size=20,
                            tooltip="Add new prescription",
                        ),
                    ],
                    spacing=10,
                ),
                Divider(height=1, color=Colors.BLACK12),
                Column(
                    controls=[prescription_card(p) for p in prescriptions],
                    spacing=10,
                    scroll=ScrollMode.ADAPTIVE,
                ),
            ],
            spacing=15,
            scroll=ScrollMode.ADAPTIVE,
            expand=True
        ),
        padding=15,
    )

    # Create tabs
    tabs = Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            Tab(
                text="Patients",
                icon=Icons.PEOPLE_ROUNDED,
                content=patients_content,
            ),
            Tab(
                text="Records",
                icon=Icons.FOLDER_ROUNDED,
                content=records_content,
            ),
            Tab(
                text="Appointments",
                icon=Icons.CALENDAR_TODAY_ROUNDED,
                content=appointments_content,
            ),
            Tab(
                text="Prescriptions",
                icon=Icons.MEDICATION_ROUNDED,
                content=prescriptions_content,
            ),
        ],
    )

    # Main container with scrolling
    profile_container = Container(
        content=Column(
            controls=[
                profile_header,
                stats_overview,
                tabs,
            ],
            spacing=0,
            expand=True,
        ),
        padding=20,
        width=1000,
        height=1200,
        bgcolor=Colors.WHITE,
        expand=True        
    )

    # page.overlay.append(profile_container)
    # page.update()

    return profile_container

def main(page: Page):
    page.title = 'MediCare'
    page.padding = 0
    page.theme_mode = ThemeMode.LIGHT

    user = {}

    try:
        with open("user_session.txt", "r") as f:
            user["id"] = f.readline().replace("\n","")
            user["name"] = f.readline().replace("\n","")
            user["email"] = f.readline().replace("\n","")
            user["role"] = f.readline().replace("\n","")
    except:
        print("Error occured")
    print(user)

    if user == {} and user['id'] == '':
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
            main_path = os.path.join(script_dir, 'main.py')
            subprocess.Popen([sys.executable, main_path])
        except Exception as e:
            print(f"Error launching main app: {e}")
        page.window.close()

    db = HospitalDB()


    dashboard_data = db.get_dashboard_stats()

    print(dashboard_data)

    def on_hover_sidebar_button(e):
        e.control.bgcolor = Colors.GREY_200 if e.data == "true" else Colors.WHITE
        e.control.update()

    def on_click_dashboard(e):
        print("Dashboard clicked")
        right_container.content.controls = [
            create_dashboard(dashboard_data, user_info=user, page=page, db=db)
        ]
        right_container.update()

    def on_click_patients(e):
        print("Patients clicked")
        right_container.content.controls = [
            patients(db, page)
        ]
        right_container.update()

    def on_click_doctors(e):
        print("Doctors clicked")
        
        right_container.content.controls = [
            doctors_and_nurses(db, page),
        ]
        right_container.update()

    def on_click_chatbot(e):
        print("Chatbot clicked")
        right_container.content.controls = [
            chatbot_page(page)
        ]
        right_container.update()
    
    def on_click_profile_page(e):
        print("Profile Page clicked")
        right_container.content.controls = [
            profile_page(page, db)
        ]
        right_container.update()

    def logout(e):
        os.remove("user_session.txt")
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
            main_path = os.path.join(script_dir, 'main.py')
            subprocess.Popen([sys.executable, main_path])
        except Exception as e:
            print(f"Error launching main app: {e}")
        page.window.close()
        


    navbar = Container(
        content=Row(
            controls=[
                Container(
                    expand=True
                ),
                IconButton(Icons.LOGOUT_OUTLINED, on_click=logout),
            ],
        ),
        padding=padding.all(17),
        bgcolor=Colors.WHITE,
        border=Border(
            bottom=BorderSide(
                color=Colors.GREY_300,
                width=1,
            ),
        ),
    )

    global right_container
    right_container = Container(
        content=Column(
            controls=[
                create_dashboard(dashboard_data, user_info=user, page=page, db=db)
            ],
        ),
        alignment=alignment.top_left,
        expand=True,
        width=page.width - 280,
    )

    container = Container(
        content=Column(
            controls=[
                navbar,
                right_container
            ],
            scroll=ScrollMode.ADAPTIVE
        ),
        alignment=alignment.top_left,
        expand=True,
        width=page.width - 280,
    )

    sidebar = Container(
        width=280,
        bgcolor=Colors.WHITE,
        content=Column(
            controls=[
                # Logo section
                Container(
                    content=Row(
                        controls=[
                            Image(
                                src="images/logo.png",
                                width=32,
                                height=32,
                            ),
                            Text(
                                "MediCare",
                                size=24,
                                weight=FontWeight.BOLD,
                                color=Colors.BLUE_700,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    border=Border(
                        bottom=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                    ),
                    padding=padding.all(20),
                ),
                # Menu items
                ListView(
                    controls=[
                        Container(
                            content=Row(
                                controls=[
                                    Icon(Icons.AUTO_GRAPH_SHARP, color=Colors.BLACK87),
                                    Text("Dashboard", weight=FontWeight.W_600),
                                ],
                            ),
                            width=300,
                            height=40,
                            on_click=on_click_dashboard,
                            padding=padding.only(left=20, bottom=10),
                            on_hover=on_hover_sidebar_button,
                            margin=margin.all(10),
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                        Container(
                            content=Row(
                                controls=[
                                    Icon(Icons.PEOPLE, color=Colors.BLACK87),
                                    Text("Patients", weight=FontWeight.W_600),
                                ],
                            ),
                            width=300,
                            height=40,
                            on_click=on_click_patients,
                            padding=padding.only(left=20, bottom=10),
                            on_hover=on_hover_sidebar_button,
                            margin=margin.all(10),
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                        Container(
                            content=Row(
                                controls=[
                                    Icon(Icons.MEDICAL_SERVICES, color=Colors.BLACK87),
                                    Text("Doctors", weight=FontWeight.W_600),
                                ],
                            ),
                            width=300,
                            height=40,
                            on_click=on_click_doctors,
                            padding=padding.only(left=20, bottom=10),
                            on_hover=on_hover_sidebar_button,
                            margin=margin.all(10),
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                        Container(
                            content=Row(
                                controls=[
                                    Icon(Icons.CHAT, color=Colors.BLACK87),
                                    Text("Chatbot", weight=FontWeight.W_600),
                                ],
                            ),
                            width=300,
                            height=40,
                            on_click=on_click_chatbot,
                            padding=padding.only(left=20, bottom=10),
                            on_hover=on_hover_sidebar_button,
                            margin=margin.all(10),
                            border_radius=BorderRadius(
                                top_left=20,
                                bottom_left=20,
                                top_right=20,
                                bottom_right=20,
                            ),
                        ),
                    ],
                ),
                Container(
                    expand=True,
                    border=Border(
                        bottom=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                    ),
                ),
                # User section
                Container(
                    content=Row(
                        controls=[
                            Container(
                                content=Icon(Icons.PERSON, color=Colors.GREY_600),
                                padding=padding.all(10),
                            ),
                            Column(
                                controls=[
                                    Text(
                                        user["name"],
                                        size=16,
                                        color=Colors.BLACK87,
                                    ),
                                    Text(
                                        user["email"],
                                        size=14,
                                        color=Colors.GREY_600,
                                    ),
                                    Text(
                                        user["role"],
                                        size=14,
                                        color=Colors.GREY_600,
                                    ),
                                ],
                                spacing=0
                            ),
                        ]
                    ),
                    margin=margin.all(10),
                    border=Border(
                        top=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                        left=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                        right=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                        bottom=BorderSide(
                            color=Colors.GREY_300,
                            width=1,
                        ),
                    ),
                    border_radius=BorderRadius(
                        top_left=20,
                        bottom_left=20,
                        top_right=20,
                        bottom_right=20,
                    ),
                    padding=padding.all(20),
                    on_click=on_click_profile_page
                )
            ],
        ),
        border=Border(
            right=BorderSide(
                color=Colors.GREY_300,
                width=1,
            ),
        ),
    )

    main_container = Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar,
            container,
        ]
    )

    page.add(main_container)

if __name__ == '__main__':
    app(target=main)