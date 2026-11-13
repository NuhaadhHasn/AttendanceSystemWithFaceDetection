"""Drawing the window."""
import numpy as np
import pytest

from attendance import MODE_ALREADY_MARKED, MODE_DETAILS, MODE_IDLE, MODE_MARKED, Frame
from helpers import employee
from ui import (CAM_H, CAM_W, CAM_X, CAM_Y, PANEL_H, PANEL_W, PANEL_X, PANEL_Y, PHOTO_X, PHOTO_Y,
                compose, face_bbox)


@pytest.fixture
def scene():
    background = np.zeros((720, 1280, 3), np.uint8)
    cam = np.full((CAM_H, CAM_W, 3), 200, np.uint8)
    modes = [np.full((PANEL_H, PANEL_W, 3), 10 + 40 * i, np.uint8) for i in range(4)]
    return background, cam, modes


def panel(img):
    return img[PANEL_Y:PANEL_Y + PANEL_H, PANEL_X:PANEL_X + PANEL_W]


def test_face_bbox_converts_camera_pixels_to_window_pixels():
    assert face_bbox((10, 110, 90, 30)) == (CAM_X + 30, CAM_Y + 10, 80, 80)


def test_idle_screen_shows_camera_and_idle_panel_without_touching_the_background(scene):
    background, cam, modes = scene
    out = compose(background, cam, modes, Frame())
    assert out is not background and not background.any()
    assert (out[CAM_Y:CAM_Y + CAM_H, CAM_X:CAM_X + CAM_W] == 200).all()
    assert np.array_equal(panel(out), modes[MODE_IDLE])


@pytest.mark.parametrize("mode", [MODE_MARKED, MODE_ALREADY_MARKED])
def test_marked_and_already_marked_show_their_panel_unchanged(scene, mode):
    background, cam, modes = scene
    out = compose(background, cam, modes, Frame(mode, "001", employee()))
    assert np.array_equal(panel(out), modes[mode])


def test_details_screen_draws_text_and_the_photo(scene):
    background, cam, modes = scene
    photo = np.full((216, 216, 3), 123, np.uint8)
    out = compose(background, cam, modes, Frame(MODE_DETAILS, "001", employee(name="Ada"), photo))
    assert not np.array_equal(panel(out), modes[MODE_DETAILS])               # text was drawn
    assert (out[PHOTO_Y:PHOTO_Y + 216, PHOTO_X:PHOTO_X + 216] == 123).all()  # photo placed


def test_details_screen_survives_missing_fields_and_missing_photo(scene):
    background, cam, modes = scene
    out = compose(background, cam, modes, Frame(MODE_DETAILS, "001", {"Name": "Only A Name"}, None))
    assert out.shape == background.shape


def test_face_box_is_drawn_at_the_face(scene):
    background, cam, modes = scene
    box = (50, 250, 200, 100)                                  # top, right, bottom, left
    x, y, _, _ = face_bbox(box)
    out = compose(background, cam, modes, Frame(), boxes=[box])
    assert tuple(out[y, x + 10]) == (0, 255, 0)                # green corner marker


def test_loading_label_changes_only_the_camera_side(scene):
    background, cam, modes = scene
    plain = compose(background, cam, modes, Frame())
    loading = compose(background, cam, modes, Frame(), loading=True)
    assert not np.array_equal(plain, loading)
    assert np.array_equal(panel(plain), panel(loading))
