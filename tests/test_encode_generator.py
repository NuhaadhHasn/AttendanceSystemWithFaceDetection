"""encodeGenerator: bad photos are skipped, ids stay aligned, Storage is optional."""
import pickle
import shutil

import numpy as np
import pytest

pytest.importorskip("face_recognition")

import encodeGenerator  # noqa: E402
from helpers import ROOT  # noqa: E402

REAL = ROOT / "Images"


@pytest.fixture
def photos_dir(tmp_path):
    d = tmp_path / "Images"
    d.mkdir()
    shutil.copy(REAL / "001.png", d / "001.png")
    shutil.copy(REAL / "003.png", d / "003.png")
    return d


def test_collect_photos_keeps_only_images_sorted(photos_dir):
    (photos_dir / "notes.txt").write_text("hi")
    (photos_dir / "002.JPG").write_bytes(b"x")
    assert [p.name for p in encodeGenerator.collect_photos(photos_dir)] == ["001.png", "002.JPG", "003.png"]


def test_unusable_photos_are_skipped_and_ids_stay_aligned(photos_dir):
    import cv2
    cv2.imwrite(str(photos_dir / "002.png"), np.full((216, 216, 3), 128, np.uint8))  # no face
    (photos_dir / "004.png").write_bytes(b"not an image")                             # unreadable

    encodings, ids = encodeGenerator.find_encodings(encodeGenerator.collect_photos(photos_dir))

    assert ids == ["001", "003"]                       # 002 and 004 dropped, order kept
    assert len(encodings) == 2 and len(encodings[0]) == 128


def test_generate_writes_encodings_and_uploads(photos_dir, tmp_path):
    out = tmp_path / "EncodeFile.p"
    uploaded = []

    code = encodeGenerator.generate(photos_dir, out, upload=True, uploader=uploaded.extend)

    assert code == 0
    encodings, ids = pickle.loads(out.read_bytes())
    assert ids == ["001", "003"] and len(encodings) == 2
    assert [p.name for p in uploaded] == ["001.png", "003.png"]


def test_generate_without_upload_never_touches_storage(photos_dir, tmp_path):
    def boom(_):
        raise AssertionError("uploader must not be called")

    assert encodeGenerator.generate(photos_dir, tmp_path / "e.p", upload=False, uploader=boom) == 0


def test_generate_with_no_usable_faces_fails_and_keeps_the_old_file(tmp_path):
    empty = tmp_path / "Images"
    empty.mkdir()
    out = tmp_path / "EncodeFile.p"
    out.write_bytes(b"previous good file")

    assert encodeGenerator.generate(empty, out, upload=False) == 1
    assert out.read_bytes() == b"previous good file"


def test_storage_failure_is_reported_not_raised(monkeypatch, photos_dir):
    import store

    def broken():
        raise PermissionError("403 billing account for the owning project is disabled")

    monkeypatch.setattr(store, "init_firebase", broken)
    assert encodeGenerator.upload_to_storage(encodeGenerator.collect_photos(photos_dir)) is False


def test_storage_error_message_is_one_short_line(monkeypatch, photos_dir, caplog):
    import store

    def broken():
        raise PermissionError("403 billing disabled\n" + "{\n  \"error\": {...}\n}\n" * 50)

    monkeypatch.setattr(store, "init_firebase", broken)
    encodeGenerator.upload_to_storage(encodeGenerator.collect_photos(photos_dir))

    warning = next(r.getMessage() for r in caplog.records if "upload skipped" in r.getMessage())
    assert "\n" not in warning and "403 billing disabled" in warning and len(warning) < 260


def test_no_upload_flag_is_passed_through(monkeypatch):
    seen = {}
    monkeypatch.setattr(encodeGenerator, "generate", lambda upload: seen.setdefault("upload", upload) and 0)
    encodeGenerator.main(["--no-upload"])
    assert seen["upload"] is False
