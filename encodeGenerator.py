"""Build EncodeFile.p from the photos in Images/ (and optionally back them up to Storage).

Usage:
    python encodeGenerator.py              # encode, then upload photos to Firebase Storage
    python encodeGenerator.py --no-upload  # encode only (no Firebase needed)

The encodings file is always written first, so a Storage problem (for example
billing disabled) never blocks encoding.
"""
import argparse
import logging
import pickle
import sys
from pathlib import Path

import cv2
import face_recognition

import config

log = logging.getLogger("encoder")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def collect_photos(images_dir):
    """Image files in `images_dir`, sorted by name. Other files are ignored."""
    return sorted(p for p in Path(images_dir).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def find_encodings(photos):
    """Encode one face per photo.

    Returns (encodings, ids). Photos that cannot be read or contain no face are
    skipped with a warning, and ids stay aligned with encodings.
    """
    encodings, ids = [], []
    for path in photos:
        img = cv2.imread(str(path))
        if img is None:
            log.warning("Skipped %s: not a readable image.", path.name)
            continue
        found = face_recognition.face_encodings(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not found:
            log.warning("Skipped %s: no face found. Use a clear, front-facing photo.", path.name)
            continue
        if len(found) > 1:
            log.warning("%s contains %d faces; using the first.", path.name, len(found))
        encodings.append(found[0])
        ids.append(path.stem)
    return encodings, ids


def upload_to_storage(photos):
    """Best-effort upload of the photos to Firebase Storage. Returns True on success."""
    try:
        from store import init_firebase
        init_firebase()
        from firebase_admin import storage
        bucket = storage.bucket()
        for path in photos:
            bucket.blob(f"Images/{path.name}").upload_from_filename(str(path))
        log.info("Uploaded %d photos to Firebase Storage.", len(photos))
        return True
    except Exception as exc:
        # Google's errors can run to dozens of lines of JSON; show only the first.
        lines = [ln.strip() for ln in str(exc).splitlines() if ln.strip()]
        summary = (lines[0] if lines else type(exc).__name__)[:200]
        log.warning("Storage upload skipped: %s", summary)
        log.warning("This is fine: the app reads photos from the local Images/ folder.")
        return False


def generate(images_dir=config.IMAGES_DIR, output=config.ENCODINGS_FILE, upload=True,
             uploader=upload_to_storage):
    """Encode every photo and save the result. Returns a process exit code."""
    photos = collect_photos(images_dir)
    log.info("Encoding %d photos ...", len(photos))
    encodings, ids = find_encodings(photos)
    if not encodings:
        log.error("No usable faces found in %s. Nothing was written.", images_dir)
        return 1

    with open(output, "wb") as f:
        pickle.dump((encodings, ids), f)
    log.info("Saved %d encodings (%s) to %s", len(ids), ", ".join(ids), Path(output).name)

    if upload:
        uploader(photos)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--no-upload", action="store_true", help="skip the Firebase Storage upload")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return generate(upload=not args.no_upload)


if __name__ == "__main__":
    sys.exit(main())
