"""Matching a face against the known encodings, and detecting faces in frames."""
import numpy as np
import pytest
from helpers import ROOT, blank_frame, webcam_frame_with_face

from recognition import find_faces, identify

IDS = ["001", "002", "003"]


def unit(i, dims=128):
    v = np.zeros(dims)
    v[i] = 1.0
    return v


KNOWN = [unit(0), unit(1), unit(2)]


def test_identify_returns_the_closest_id():
    assert identify(unit(1) + 0.01, KNOWN, IDS) == "002"


def test_identify_rejects_a_stranger():
    stranger = np.full(128, 0.5)                      # far from all three
    assert identify(stranger, KNOWN, IDS) is None


def test_identify_tolerance_is_inclusive_and_configurable():
    probe = unit(0).copy()
    probe[5] = 0.6                                    # distance exactly 0.6 from 001
    assert identify(probe, KNOWN, IDS, tolerance=0.6) == "001"
    assert identify(probe, KNOWN, IDS, tolerance=0.5) is None


def test_identify_with_nobody_enrolled():
    assert identify(unit(0), [], []) is None


face_recognition = pytest.importorskip("face_recognition")


def test_find_faces_detects_one_face_and_scales_the_box_back_up():
    frame = webcam_frame_with_face(ROOT / "Images" / "001.png")
    faces = find_faces(frame)
    assert len(faces) == 1
    encoding, (top, right, bottom, left) = faces[0]
    assert len(encoding) == 128
    assert 0 <= top < bottom <= 480 and 0 <= left < right <= 640   # full-frame pixels
    assert bottom - top > 100                                       # a real face-sized box


def test_find_faces_on_an_empty_scene_finds_nothing():
    assert find_faces(blank_frame()) == []


def test_every_enrolled_photo_is_recognised_as_itself():
    from encodeGenerator import collect_photos, find_encodings

    photos = collect_photos(ROOT / "Images")
    encodings, ids = find_encodings(photos)
    assert ids == [p.stem for p in photos]            # nobody was skipped
    for photo in photos:
        (enc, _), = find_faces(webcam_frame_with_face(photo))
        assert identify(enc, encodings, ids) == photo.stem
