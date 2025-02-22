import requests
import json
import smtplib
from email.mime.text import MIMEText
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

USERNAME = os.environ.get("ACC_USERNAME")
PASSWORD = os.environ.get("PASSWORD")
STUDENT_ID = os.environ.get("STUDENT_ID")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")


# University API URLs
LOGIN_URL = "http://newecom.fci.cu.edu.eg/api/authenticate"
GRADES_URL = f"http://newecom.fci.cu.edu.eg/api/student-courses?size=150&studentId.equals={STUDENT_ID}&includeWithdraw.equals=true"



def login():
    """Logs into the university system and returns an authentication token."""
    data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(LOGIN_URL, json=data)
    
    if response.status_code == 200:
        token = response.json().get("id_token")
        print("[✅] Login successful!")
        return token
    else:
        print("[❌] Login failed!")
        return None

def get_grades(token):
    """Fetches the current grades using the authentication token."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(GRADES_URL, headers=headers)

    if response.status_code == 200:
        courses = response.json()
        print("[ℹ️] API Response:", json.dumps(courses, indent=2))  # Debugging line
        
        try:
            grades = {course["course"]["name"]: course.get("grade") for course in courses}
            return grades
        except (KeyError, TypeError):
            print("[❌] Unexpected response format!")
            return None
    else:
        print("[❌] Failed to fetch grades!")
        return None

def send_email(subject, message):
    """Sends an email notification when grades are updated."""
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    print("[✅] Email sent!")

def check_for_updates():
    """Continuously monitors for new grades and sends notifications."""
    token = login()
    if not token:
        return
    
    try:
        with open("grades.json", "r") as file:
            old_grades = json.load(file)
    except FileNotFoundError:
        old_grades = {}
    
    while True:
        new_grades = get_grades(token)
        if not new_grades:
            return

        updated = False
        for course, grade in new_grades.items():
            old_grade = old_grades.get(course)
            if old_grade is None and grade is not None:  # Check if a grade changed from None to a value
                updated = True
                break

        if updated:
            message = "📢 Your grades have been updated!\n\n"            
            send_email("Your Grades Have Been Updated!", message)
            
            with open("grades.json", "w") as file:
                json.dump(new_grades, file)
        else:
            print("[ℹ️] No new updates.")
        
        time.sleep(60)  # Check every 5 minutes

if __name__ == "__main__":
    check_for_updates()
