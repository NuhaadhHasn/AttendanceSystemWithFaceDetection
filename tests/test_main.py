"""End-to-end: the real main loop, with a simulated camera and an in-memory database."""
import importlib
import pickle
from datetime import timedelta

import numpy as np
import pytest

pytest.importorskip("face_recognition")

import config  # noqa: E402
import main  # noqa: E402
from attendance import (MODE_ALREADY_MARKED, MODE_DETAILS, MODE_IDLE, MODE_MARKED,  # noqa: E402
                        AttendanceSession)
from encodeGenerator import collect_photos, find_encodings  # noqa: E402
from helpers import NOW, ROOT, FakeStore, blank_frame, employee, webcam_frame_with_face  # noqa: E402
from ui import PANEL_H, PANEL_W, PANEL_X, PANEL_Y  # noqa: E402


@pytest.fixture(scope="module")
def known():
    return find_encodings(collect_photos(ROOT / "Images"))


@pytest.fixture(scope="module")
def assets():
    return main.load_assets()


class ScriptedCamera:
    """`idle` blank frames, then the person's face forever."""

    def __init__(self, idle=3, face=None):
        self.idle, self.face, self.reads = idle, face, 0

    def read(self):
        self.reads += 1
        return True, (blank_frame() if self.reads <= self.idle else self.face.copy())


class Clock:
    """Advances a quarter of a second every frame, whatever the real speed."""

    def __init__(self, step=0.25):
        self.t, self.step = NOW, timedelta(seconds=step)

    def __call__(self):
        self.t += self.step
        return self.t


def run_loop(store, known, assets, camera, max_frames, **kw):
    session = AttendanceSession(store, photo_loader=lambda i: None, cooldown=30)
    modes, panels = [], []
    update = session.update

    def spy(*a, **k):
        frame = update(*a, **k)
        modes.append(frame.mode)
        return frame

    session.update = spy

    def show(img):
        panels.append(img[PANEL_Y:PANEL_Y + PANEL_H, PANEL_X:PANEL_X + PANEL_W].copy())
        return False

    code = main.run(camera, session, assets, known, show, clock=Clock(), max_frames=max_frames, **kw)
    return code, modes, panels


def compress(seq):
    return [m for i, m in enumerate(seq) if i == 0 or m != seq[i - 1]]


def test_full_attendance_flow(known, assets):
    store = FakeStore({"001": employee(total=5)})
    camera = ScriptedCamera(idle=3, face=webcam_frame_with_face(ROOT / "Images" / "001.png"))

    code, modes, panels = run_loop(store, known, assets, camera, max_frames=40)

    assert code == 0
    # waiting -> profile -> marked -> (still in view) already marked
    assert compress(modes)[:5] == [MODE_IDLE, MODE_DETAILS, MODE_MARKED, MODE_IDLE, MODE_ALREADY_MARKED]
    assert len(store.marks) == 1                       # marked exactly once, never twice
    assert store.marks[0][:2] == ("001", 6)
    assert len(panels) > 40                            # extra "Loading" frames were shown too


def test_unknown_person_is_never_marked(known, assets):
    encodings, ids = known
    strangers = ([e for e, i in zip(encodings, ids) if i != "001"], [i for i in ids if i != "001"])
    store = FakeStore({"001": employee()})
    camera = ScriptedCamera(idle=0, face=webcam_frame_with_face(ROOT / "Images" / "001.png"))

    code, modes, _ = run_loop(store, strangers, assets, camera, max_frames=6)

    assert code == 0 and set(modes) == {MODE_IDLE}
    assert store.get_calls == [] and store.marks == []


def test_user_can_quit(known, assets):
    session = AttendanceSession(FakeStore(), photo_loader=lambda i: None)
    shown = []

    def show(img):
        shown.append(1)
        return len(shown) >= 3                          # user presses q on the 3rd frame

    camera = ScriptedCamera(idle=100, face=blank_frame())
    assert main.run(camera, session, assets, known, show) == 0
    assert len(shown) == 3


def test_dead_camera_exits_with_an_error_instead_of_crashing(known, assets):
    class DeadCamera:
        def read(self):
            return False, None

    session = AttendanceSession(FakeStore(), photo_loader=lambda i: None)
    assert main.run(DeadCamera(), session, assets, known, lambda img: False, max_read_failures=3) == 1


def test_camera_with_a_different_resolution_is_resized_not_fatal(known, assets):
    class SmallCamera:
        def read(self):
            return True, blank_frame(320, 240)

    session = AttendanceSession(FakeStore(), photo_loader=lambda i: None)
    assert main.run(SmallCamera(), session, assets, known, lambda img: False, max_frames=2) == 0


# --- start-up checks --------------------------------------------------------
def test_load_encodings_roundtrip(tmp_path, known):
    f = tmp_path / "EncodeFile.p"
    f.write_bytes(pickle.dumps(known))  # test-generated data, never untrusted input
    encodings, ids = main.load_encodings(f)
    assert ids == known[1] and len(encodings) == len(known[0])


def test_load_encodings_missing_file_says_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="encodeGenerator.py"):
        main.load_encodings(tmp_path / "nope.p")


def test_load_encodings_rejects_empty_file(tmp_path):
    f = tmp_path / "EncodeFile.p"
    f.write_bytes(pickle.dumps(([], [])))
    with pytest.raises(ValueError):
        main.load_encodings(f)


def test_load_assets_finds_all_ui_images(assets):
    background, modes = assets
    assert background.shape[:2] == (720, 1280) and len(modes) == 4


def test_main_reports_missing_encodings_and_exits_1(monkeypatch, caplog):
    def missing(*a, **k):
        raise FileNotFoundError("EncodeFile.p not found. Run `python encodeGenerator.py` first.")

    monkeypatch.setattr(main, "load_encodings", missing)
    assert main.main() == 1
    assert "encodeGenerator.py" in caplog.text


def test_main_reports_camera_that_cannot_open(monkeypatch, known, caplog):
    class ClosedCamera:
        def isOpened(self):
            return False

    monkeypatch.setattr(main, "load_encodings", lambda *a, **k: known)
    monkeypatch.setattr(main, "FirebaseStore", FakeStore)
    monkeypatch.setattr(main.cv2, "VideoCapture", lambda *a: ClosedCamera())
    assert main.main() == 1
    assert "Could not open camera" in caplog.text


# --- config and Firebase init ----------------------------------------------
def test_config_values_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("COOLDOWN_SECONDS", "86400")
    monkeypatch.setenv("CAMERA_INDEX", "2")
    monkeypatch.setenv("FIREBASE_DATABASE_URL", "https://example.test/")
    try:
        importlib.reload(config)
        assert (config.COOLDOWN_SECONDS, config.CAMERA_INDEX, config.DATABASE_URL) == (86400, 2, "https://example.test/")
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_init_firebase_without_a_key_file_explains_how_to_get_one(monkeypatch, tmp_path):
    import store
    monkeypatch.setattr(store.config, "SERVICE_ACCOUNT_KEY", tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="Service accounts"):
        store.init_firebase()
