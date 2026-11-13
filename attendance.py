"""Attendance rules and the on-screen state machine.

Nothing here touches the camera, the screen or Firebase directly, so the whole
module can be tested with a fake store and a fake clock.
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import cv2
import numpy as np

import config

log = logging.getLogger(__name__)

# Indexes of the right-hand panel images (Resources/Modes/1.png .. 4.png)
MODE_IDLE = 0
MODE_DETAILS = 1
MODE_MARKED = 2
MODE_ALREADY_MARKED = 3


def seconds_since(last_time: Optional[str], now: datetime) -> float:
    """Seconds between `last_time` ("YYYY-MM-DD HH:MM:SS") and `now`.

    A missing timestamp means the person has never been marked, so it counts as
    infinitely long ago. A malformed timestamp raises ValueError.
    """
    if not last_time:
        return math.inf
    return (now - datetime.strptime(last_time, config.TIME_FORMAT)).total_seconds()


def load_employee_photo(employee_id: str, images_dir=config.IMAGES_DIR, bucket=None,
                        size=config.PHOTO_SIZE):
    """Return the employee's photo as a BGR image of `size`, or None.

    The local Images/ folder is tried first, so the app works offline and does
    not depend on Firebase Storage. Storage is only a fallback, and any error
    from it is logged instead of crashing the app.
    """
    path = Path(images_dir) / f"{employee_id}.png"
    img = cv2.imread(str(path)) if path.is_file() else None

    if img is None and bucket is not None:
        try:
            blob = bucket.get_blob(f"Images/{employee_id}.png")
            if blob is not None:
                data = np.frombuffer(blob.download_as_bytes(), np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception as exc:  # network, permission, billing ...
            log.warning("Could not fetch photo for %s from Storage: %s", employee_id, exc)

    if img is None:
        return None
    if (img.shape[1], img.shape[0]) != tuple(size):
        img = cv2.resize(img, tuple(size))
    return img


@dataclass
class Frame:
    """What the UI should show right now."""
    mode: int = MODE_IDLE
    employee_id: Optional[str] = None
    employee: Optional[Dict[str, Any]] = None
    photo: Any = None


@dataclass
class _Active:
    employee_id: str
    employee: Dict[str, Any]
    photo: Any
    started: datetime
    marked: bool  # True: just marked now. False: was already marked.


class AttendanceSession:
    """Decides what to show and when to write attendance.

    Call `update()` once per camera frame with the recognised employee id (or
    None). The profile is fetched and attendance written ONCE per sighting; the
    screens then advance by wall-clock time, so the behaviour no longer depends
    on how fast frames are processed.
    """

    def __init__(self, store, photo_loader: Callable[[str], Any],
                 cooldown: float = config.COOLDOWN_SECONDS,
                 details_seconds: float = config.DETAILS_SECONDS,
                 marked_seconds: float = config.MARKED_SECONDS,
                 already_seconds: float = config.ALREADY_MARKED_SECONDS,
                 retry_seconds: float = config.STORE_RETRY_SECONDS):
        self.store = store
        self.photo_loader = photo_loader
        self.cooldown = cooldown
        self.details_seconds = details_seconds
        self.marked_seconds = marked_seconds
        self.already_seconds = already_seconds
        self.retry_seconds = retry_seconds
        self._active: Optional[_Active] = None
        self._photos: Dict[str, Any] = {}
        self._retry_until: Dict[str, datetime] = {}

    def update(self, employee_id: Optional[str], now: datetime,
               on_loading: Optional[Callable[[], None]] = None) -> Frame:
        if employee_id is None:
            self._active = None
            return Frame()

        if self._active is not None and self._active.employee_id != employee_id:
            self._active = None

        if self._active is None:
            retry_at = self._retry_until.get(employee_id)
            if retry_at is not None and now < retry_at:
                return Frame()
            if on_loading is not None:
                on_loading()
            self._active = self._begin(employee_id, now)
            if self._active is None:
                self._retry_until[employee_id] = now + timedelta(seconds=self.retry_seconds)
                return Frame()
            self._retry_until.pop(employee_id, None)

        return self._frame(now)

    # ------------------------------------------------------------------
    def _begin(self, employee_id: str, now: datetime) -> Optional[_Active]:
        """Fetch the profile and, if the cool-down is over, mark attendance."""
        try:
            employee = self.store.get_employee(employee_id)
            if not employee:
                log.warning("Recognised %s but there is no database record for them.", employee_id)
                return None

            marked = seconds_since(employee.get("Last_Attendance_Time"), now) > self.cooldown
            if marked:
                total = int(employee.get("Total_Attendance") or 0) + 1
                stamp = now.strftime(config.TIME_FORMAT)
                self.store.mark_attendance(employee_id, total, stamp)
                employee = {**employee, "Total_Attendance": total, "Last_Attendance_Time": stamp}
                log.info("Marked attendance for %s (total %d)", employee_id, total)
            else:
                log.info("%s was already marked recently.", employee_id)
        except Exception as exc:
            log.error("Could not process attendance for %s: %s", employee_id, exc)
            return None

        if employee_id not in self._photos:
            self._photos[employee_id] = self.photo_loader(employee_id)
        return _Active(employee_id, employee, self._photos[employee_id], now, marked)

    def _frame(self, now: datetime) -> Frame:
        a = self._active
        elapsed = (now - a.started).total_seconds()
        if a.marked:
            if elapsed < self.details_seconds:
                mode = MODE_DETAILS
            elif elapsed < self.details_seconds + self.marked_seconds:
                mode = MODE_MARKED
            else:
                self._active = None
                return Frame()
        else:
            if elapsed < self.already_seconds:
                mode = MODE_ALREADY_MARKED
            else:
                self._active = None
                return Frame()
        return Frame(mode, a.employee_id, a.employee, a.photo)
