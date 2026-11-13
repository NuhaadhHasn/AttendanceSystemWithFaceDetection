"""Firebase access: one place that initialises the app and talks to the database."""
import logging

import config

log = logging.getLogger(__name__)


def init_firebase():
    """Initialise the Firebase Admin SDK once and return the `firebase_admin` module."""
    import firebase_admin
    from firebase_admin import credentials

    if not firebase_admin._apps:
        if not config.SERVICE_ACCOUNT_KEY.is_file():
            raise FileNotFoundError(
                f"Firebase key not found at {config.SERVICE_ACCOUNT_KEY}. Download it from "
                "Firebase console > Project settings > Service accounts and save it there "
                "(or set SERVICE_ACCOUNT_KEY)."
            )
        firebase_admin.initialize_app(
            credentials.Certificate(str(config.SERVICE_ACCOUNT_KEY)),
            {"databaseURL": config.DATABASE_URL, "storageBucket": config.STORAGE_BUCKET},
        )
    return firebase_admin


class FirebaseStore:
    """Employee records in the Firebase Realtime Database."""

    def __init__(self):
        init_firebase()

    def get_employee(self, employee_id):
        from firebase_admin import db
        return db.reference(f"Employees/{employee_id}").get()

    def mark_attendance(self, employee_id, total_attendance, timestamp):
        """Write the new total and time in a single atomic update."""
        from firebase_admin import db
        db.reference(f"Employees/{employee_id}").update({
            "Total_Attendance": total_attendance,
            "Last_Attendance_Time": timestamp,
        })

    def bucket(self):
        """The Storage bucket, or None if it cannot be created. Storage is optional."""
        try:
            from firebase_admin import storage
            return storage.bucket()
        except Exception as exc:
            log.warning("Firebase Storage unavailable: %s", exc)
            return None
