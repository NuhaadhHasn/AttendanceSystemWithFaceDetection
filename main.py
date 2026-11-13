"""Attendance system with face recognition: live camera window.

Run `python encodeGenerator.py` once first, then `python main.py`.
Press q or Esc (or close the window) to quit.
"""
import logging
import pickle
import sys
import time
from datetime import datetime
from functools import partial

import cv2

import config
from attendance import AttendanceSession, Frame, load_employee_photo
from recognition import find_faces, identify
from store import FirebaseStore
from ui import CAM_H, CAM_W, compose

log = logging.getLogger("attendance")

WINDOW = "Attendance With Face Recognition"


def load_assets():
    """Load the window background and the four status-panel images."""
    background = cv2.imread(str(config.BACKGROUND_IMAGE))
    modes = [cv2.imread(str(config.MODES_DIR / f"{i}.png")) for i in range(1, 5)]
    if background is None or any(m is None for m in modes):
        raise FileNotFoundError(
            f"Missing UI images. Expected {config.BACKGROUND_IMAGE} and 1.png-4.png in {config.MODES_DIR}."
        )
    return background, modes


def load_encodings(path=config.ENCODINGS_FILE):
    """Load (face encodings, employee ids) written by encodeGenerator.py."""
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} not found. Run `python encodeGenerator.py` first.")
    # SECURITY: unpickling can run arbitrary code. This file is produced locally by
    # encodeGenerator.py and is git-ignored. Never load an EncodeFile.p from someone else.
    with open(path, "rb") as f:
        encodings, ids = pickle.load(f)
    if len(encodings) == 0 or len(encodings) != len(ids):
        raise ValueError(f"{path.name} is empty or corrupt. Re-run `python encodeGenerator.py`.")
    return encodings, ids


def run(capture, session, assets, known, show, clock=datetime.now, max_frames=None,
        max_read_failures=30):
    """Main loop. Returns a process exit code.

    capture: object with read() -> (ok, frame)
    show:    show(image) -> True when the user asked to quit
    """
    background, modes = assets
    known_encodings, known_ids = known
    failures = 0
    frames = 0

    while True:
        ok, img = capture.read()
        if not ok or img is None:
            failures += 1
            if failures >= max_read_failures:
                log.error("The camera stopped delivering frames.")
                return 1
            time.sleep(0.05)
            continue
        failures = 0
        if img.shape[:2] != (CAM_H, CAM_W):
            img = cv2.resize(img, (CAM_W, CAM_H))

        boxes, employee_id = [], None
        for encoding, box in find_faces(img):
            matched = identify(encoding, known_encodings, known_ids, config.MATCH_TOLERANCE)
            if matched is not None:
                boxes.append(box)
                employee_id = employee_id or matched

        def show_loading():
            show(compose(background, img, modes, Frame(), boxes, loading=True))

        frame = session.update(employee_id, clock(), on_loading=show_loading)
        if show(compose(background, img, modes, frame, boxes)):
            return 0

        frames += 1
        if max_frames is not None and frames >= max_frames:
            return 0


def _window_show(image):
    cv2.imshow(WINDOW, image)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord("q"), 27):
        return True
    try:
        return cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1  # window closed
    except cv2.error:
        return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        assets = load_assets()
        known = load_encodings()
        store = FirebaseStore()
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1

    capture = cv2.VideoCapture(config.CAMERA_INDEX)
    if not capture.isOpened():
        log.error("Could not open camera %d. Check it is connected and not used by another app.",
                  config.CAMERA_INDEX)
        return 1
    capture.set(3, CAM_W)
    capture.set(4, CAM_H)

    photo_loader = partial(load_employee_photo, bucket=store.bucket())
    session = AttendanceSession(store, photo_loader)
    log.info("Ready. Look at the camera. Press q to quit.")
    try:
        return run(capture, session, assets, known, _window_show)
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
