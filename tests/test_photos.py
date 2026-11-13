"""Employee photo loading: local folder first, Storage only as a fallback."""
import cv2
import numpy as np

from attendance import load_employee_photo


def write_png(path, size=(100, 100)):
    img = np.random.randint(0, 255, (size[1], size[0], 3), dtype=np.uint8)
    cv2.imwrite(str(path), img)
    return img


class FakeBlob:
    def __init__(self, data):
        self.data = data

    def download_as_bytes(self):
        return self.data


class FakeBucket:
    def __init__(self, blob=None, error=None):
        self.blob, self.error, self.requested = blob, error, []

    def get_blob(self, name):
        self.requested.append(name)
        if self.error:
            raise self.error
        return self.blob


def test_local_photo_is_loaded_and_resized_to_216(tmp_path):
    write_png(tmp_path / "001.png", size=(100, 100))
    img = load_employee_photo("001", images_dir=tmp_path)
    assert img.shape == (216, 216, 3)


def test_local_photo_wins_over_storage(tmp_path):
    write_png(tmp_path / "001.png", size=(216, 216))
    bucket = FakeBucket()
    assert load_employee_photo("001", images_dir=tmp_path, bucket=bucket) is not None
    assert bucket.requested == []


def test_missing_photo_without_storage_returns_none(tmp_path):
    assert load_employee_photo("404", images_dir=tmp_path) is None


def test_storage_error_is_swallowed(tmp_path):
    """e.g. 403 billing disabled: the app must carry on, not crash."""
    bucket = FakeBucket(error=PermissionError("403 billing account disabled"))
    assert load_employee_photo("001", images_dir=tmp_path, bucket=bucket) is None
    assert bucket.requested == ["Images/001.png"]


def test_storage_fallback_decodes_the_image(tmp_path):
    ok, encoded = cv2.imencode(".png", np.full((300, 300, 3), 90, np.uint8))
    bucket = FakeBucket(blob=FakeBlob(encoded.tobytes()))
    img = load_employee_photo("001", images_dir=tmp_path, bucket=bucket)
    assert img.shape == (216, 216, 3)


def test_storage_blob_not_found_returns_none(tmp_path):
    assert load_employee_photo("001", images_dir=tmp_path, bucket=FakeBucket(blob=None)) is None


def test_corrupt_local_file_returns_none(tmp_path):
    (tmp_path / "001.png").write_bytes(b"this is not a png")
    assert load_employee_photo("001", images_dir=tmp_path) is None
