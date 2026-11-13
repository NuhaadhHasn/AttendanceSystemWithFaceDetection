"""Attendance rules and the on-screen state machine."""
import math
from datetime import timedelta

import pytest
from helpers import LONG_AGO, NOW, FakeStore, employee

from attendance import (MODE_ALREADY_MARKED, MODE_DETAILS, MODE_IDLE, MODE_MARKED,
                        AttendanceSession, seconds_since)

NOW_STR = "2026-01-01 12:00:00"


def sec(n):
    return NOW + timedelta(seconds=n)


def make_session(store, **kwargs):
    defaults = dict(cooldown=30, details_seconds=1.5, marked_seconds=1.5,
                    already_seconds=2.0, retry_seconds=5.0)
    defaults.update(kwargs)
    return AttendanceSession(store, photo_loader=lambda _id: "PHOTO", **defaults)


# --- seconds_since ----------------------------------------------------------
def test_seconds_since_measures_the_gap():
    assert seconds_since("2026-01-01 11:59:30", NOW) == 30


def test_seconds_since_missing_timestamp_means_never():
    assert seconds_since(None, NOW) == math.inf
    assert seconds_since("", NOW) == math.inf


def test_seconds_since_rejects_malformed_timestamp():
    with pytest.raises(ValueError):
        seconds_since("yesterday", NOW)


# --- marking attendance -----------------------------------------------------
def test_first_sighting_marks_attendance_and_shows_details_then_marked_then_idle():
    store = FakeStore({"001": employee(total=5)})
    s = make_session(store)

    f = s.update("001", NOW)
    assert f.mode == MODE_DETAILS
    assert f.employee["Total_Attendance"] == 6          # shows the NEW total
    assert f.photo == "PHOTO"
    assert store.marks == [("001", 6, NOW_STR)]

    assert s.update("001", sec(1.4)).mode == MODE_DETAILS
    assert s.update("001", sec(1.6)).mode == MODE_MARKED
    assert s.update("001", sec(2.9)).mode == MODE_MARKED
    assert s.update("001", sec(3.1)).mode == MODE_IDLE

    assert len(store.marks) == 1                         # written once, not per frame
    assert store.get_calls == ["001"]                    # fetched once, not per frame


def test_recently_marked_person_sees_already_marked_and_nothing_is_written():
    store = FakeStore({"001": employee(last="2026-01-01 11:59:50")})  # 10 s ago
    s = make_session(store)

    assert s.update("001", NOW).mode == MODE_ALREADY_MARKED
    assert s.update("001", sec(1.9)).mode == MODE_ALREADY_MARKED
    assert s.update("001", sec(2.1)).mode == MODE_IDLE
    assert store.marks == []


def test_cooldown_boundary_is_strictly_greater_than():
    exactly = FakeStore({"001": employee(last="2026-01-01 11:59:30")})   # exactly 30 s
    assert make_session(exactly).update("001", NOW).mode == MODE_ALREADY_MARKED

    just_over = FakeStore({"001": employee(last="2026-01-01 11:59:29")})  # 31 s
    assert make_session(just_over).update("001", NOW).mode == MODE_DETAILS


def test_person_who_stays_in_view_gets_already_marked_not_marked_again():
    """The scenario that broke when the on-screen cycle was counted in frames."""
    store = FakeStore({"001": employee()})
    s = make_session(store)

    s.update("001", NOW)                                  # marked
    assert s.update("001", sec(3.1)).mode == MODE_IDLE    # cycle finished
    assert s.update("001", sec(3.2)).mode == MODE_ALREADY_MARKED
    assert len(store.marks) == 1


def test_missing_fields_are_handled():
    store = FakeStore({"001": {"Name": "No History"}})    # no time, no total
    f = make_session(store).update("001", NOW)
    assert f.mode == MODE_DETAILS
    assert store.marks == [("001", 1, NOW_STR)]


# --- loading callback -------------------------------------------------------
def test_loading_callback_runs_once_per_sighting_before_the_fetch():
    store = FakeStore({"001": employee()})
    s = make_session(store)
    seen = []

    s.update("001", NOW, on_loading=lambda: seen.append(list(store.get_calls)))
    s.update("001", sec(0.5), on_loading=lambda: seen.append("again"))
    assert seen == [[]]                                   # called once, before get_employee


# --- resetting --------------------------------------------------------------
def test_face_leaving_resets_and_next_sighting_starts_fresh():
    store = FakeStore({"001": employee()})
    s = make_session(store)

    s.update("001", NOW)
    assert s.update(None, sec(0.5)).mode == MODE_IDLE
    s.update("001", sec(1.0))
    assert store.get_calls == ["001", "001"]


def test_switching_person_shows_the_new_person():
    store = FakeStore({"001": employee(name="A"), "002": employee(name="B")})
    s = make_session(store)

    assert s.update("001", NOW).employee["Name"] == "A"
    f = s.update("002", sec(0.5))
    assert f.employee_id == "002" and f.employee["Name"] == "B"
    assert [m[0] for m in store.marks] == ["001", "002"]


def test_photo_is_loaded_once_per_person():
    calls = []
    store = FakeStore({"001": employee()})
    s = AttendanceSession(store, photo_loader=lambda i: calls.append(i) or "P", cooldown=30)
    s.update("001", NOW)
    s.update(None, sec(1))
    s.update("001", sec(2))
    assert calls == ["001"]


def test_missing_photo_does_not_break_the_screen():
    store = FakeStore({"001": employee()})
    s = AttendanceSession(store, photo_loader=lambda i: None, cooldown=30)
    f = s.update("001", NOW)
    assert f.mode == MODE_DETAILS and f.photo is None


# --- failures never crash the app -------------------------------------------
def test_unknown_employee_is_ignored_then_retried_after_backoff():
    store = FakeStore({})
    s = make_session(store)

    assert s.update("999", NOW).mode == MODE_IDLE
    assert s.update("999", sec(1)).mode == MODE_IDLE
    assert store.get_calls == ["999"]                     # backing off, no hammering
    s.update("999", sec(6))
    assert store.get_calls == ["999", "999"]              # retried after 5 s


def test_database_error_does_not_crash_and_recovers():
    store = FakeStore({"001": employee()})
    store.fail_get = True
    s = make_session(store)

    assert s.update("001", NOW).mode == MODE_IDLE
    assert s.update("001", sec(1)).mode == MODE_IDLE
    store.fail_get = False
    assert s.update("001", sec(6)).mode == MODE_DETAILS   # recovered
    assert len(store.marks) == 1


def test_failed_write_is_not_reported_as_marked():
    store = FakeStore({"001": employee()})
    store.fail_mark = True
    s = make_session(store)

    assert s.update("001", NOW).mode == MODE_IDLE
    assert store.marks == []


def test_malformed_timestamp_in_database_does_not_crash():
    store = FakeStore({"001": employee(last="not a date")})
    s = make_session(store)
    assert s.update("001", NOW).mode == MODE_IDLE
    assert store.marks == []
