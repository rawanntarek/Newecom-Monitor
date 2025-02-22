import requests
import json
import smtplib
from email.mime.text import MIMEText
import time
import threading
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

# API URLs
REGISTRATION_URL = f"http://newecom.fci.cu.edu.eg/api/student-registration-courses?studentId={STUDENT_ID}"
LOGIN_URL = "http://newecom.fci.cu.edu.eg/api/authenticate"
GRADES_URL = f"http://newecom.fci.cu.edu.eg/api/student-courses?size=150&studentId.equals={STUDENT_ID}&includeWithdraw.equals=true"

# Courses to track
TARGET_COURSES = {
    "Soft Computing",
    "Cloud Computing",
    "Selected Topics in Software Engineering-1",
    "Web Engineering",
    "Selected Labs in Software Engineering",
}


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
        return {course["course"]["name"]: course.get("grade") for course in courses}
    else:
        print("[❌] Failed to fetch grades!")
        return None


def send_email(subject, message):
    """Sends an email notification."""
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    print("[✅] Email sent:", subject)


def check_for_updates(token):
    """Continuously monitors grades and sends an email if any target course has a grade."""
    while True:
        new_grades = get_grades(token)
        if not new_grades:
            time.sleep(30)
            continue

        message = "📢 Your grades have been updated!\n\n"
        found = False

        for course in TARGET_COURSES:
            grade = new_grades.get(course)
            if grade is not None:
                message += f"grades updated"
                found = True

        if found:
            send_email("Your Grades Have Been Updated!", message)

        print("[ℹ️] No new grade updates. Checking again in 1 minute...")
        time.sleep(30)  # Check every 30 seconds


def check_registration_status(token):
    """Continuously checks if registration is open and sends an email once."""
    headers = {"Authorization": f"Bearer {token}"}
    already_notified = False  # Track if an email was already sent

    while True:
        response = requests.get(REGISTRATION_URL, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if data.get('responseCode') != -1 and not already_notified:  # Registration is open
                print("[🚀] Registration is NOW OPEN! Hurry up!")
                send_email("📢 Registration Open!", "🚀 Registration is NOW OPEN! Hurry up!")
                already_notified = True  # Avoid duplicate emails
            elif data.get('responseCode') == -1:
                print("[ℹ️] Registration is still closed.")

        else:
            print("[❌] Failed to fetch registration status!")

        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    token = login()
    if token:
        # Run both checks in parallel
        threading.Thread(target=check_registration_status, args=(token,), daemon=True).start()
        threading.Thread(target=check_for_updates, args=(token,), daemon=True).start()

        # Keep the main thread alive
        while True:
            time.sleep(1)
