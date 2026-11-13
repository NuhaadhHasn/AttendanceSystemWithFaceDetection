"""Shared fakes for the tests."""
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 1, 1, 12, 0, 0)
LONG_AGO = "2025-12-31 12:00:00"


def employee(last=LONG_AGO, total=5, name="Test Person"):
    return {
        "Name": name,
        "Occupation": "Engineer",
        "Joined_Year": 2021,
        "Total_Attendance": total,
        "Last_Attendance_Time": last,
        "Employee_Standard": "G",
        "Total_Working_Years": 2,
    }


class FakeStore:
    """In-memory stand-in for FirebaseStore that records every call."""

    def __init__(self, employees=None):
        self.employees = {k: dict(v) for k, v in (employees or {}).items()}
        self.get_calls = []
        self.marks = []
        self.fail_get = False
        self.fail_mark = False

    def get_employee(self, employee_id):
        self.get_calls.append(employee_id)
        if self.fail_get:
            raise ConnectionError("database unreachable")
        record = self.employees.get(employee_id)
        return dict(record) if record else None

    def mark_attendance(self, employee_id, total, timestamp):
        if self.fail_mark:
            raise ConnectionError("write failed")
        self.marks.append((employee_id, total, timestamp))
        self.employees[employee_id].update(Total_Attendance=total, Last_Attendance_Time=timestamp)


def webcam_frame_with_face(photo_path):
    """A 640x480 'webcam' frame showing the given photo, like a person in front of the camera."""
    face = cv2.imread(str(photo_path))
    big = cv2.resize(face, (480, 480), interpolation=cv2.INTER_CUBIC)
    background = cv2.GaussianBlur(cv2.resize(face, (640, 640))[80:560], (0, 0), 25)
    frame = background.copy()
    frame[:, 80:560] = big
    return frame


def blank_frame(width=640, height=480):
    return np.full((height, width, 3), (176, 170, 164), np.uint8)
