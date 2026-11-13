"""Face detection and matching."""
import cv2
import numpy as np

import config


def identify(encoding, known_encodings, known_ids, tolerance=config.MATCH_TOLERANCE):
    """Return the id of the closest known face, or None if nobody is close enough.

    Same rule as face_recognition.compare_faces: the closest face wins, and it
    only counts if its distance is within `tolerance`.
    """
    if len(known_encodings) == 0:
        return None
    distances = np.linalg.norm(np.asarray(known_encodings) - np.asarray(encoding), axis=1)
    best = int(np.argmin(distances))
    return known_ids[best] if distances[best] <= tolerance else None


def find_faces(frame_bgr, scale=0.25):
    """Detect faces in a camera frame.

    The frame is shrunk first (4x fewer pixels per side) to keep detection fast.
    Returns a list of (encoding, (top, right, bottom, left)) with the box
    converted back to full-frame pixels.
    """
    import face_recognition  # imported here so the rest of the app loads without dlib

    small = cv2.resize(frame_bgr, (0, 0), None, scale, scale)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)
    inv = int(round(1 / scale))
    return [
        (enc, (top * inv, right * inv, bottom * inv, left * inv))
        for enc, (top, right, bottom, left) in zip(encodings, locations)
    ]
