"""Drawing the attendance window. Pure image manipulation, no camera or Firebase."""
import cv2
import cvzone

import config
from attendance import MODE_DETAILS, Frame

# Layout of Resources/background.png (pixels)
CAM_X, CAM_Y, CAM_W, CAM_H = 55, 162, 640, 480
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 808, 44, 414, 633
PHOTO_X, PHOTO_Y = 909, 175

FONT = cv2.FONT_HERSHEY_COMPLEX
WHITE = (255, 255, 255)
GREY = (100, 100, 100)
DARK = (50, 50, 50)


def face_bbox(box):
    """(top, right, bottom, left) in camera pixels -> (x, y, w, h) on the window."""
    top, right, bottom, left = box
    return CAM_X + left, CAM_Y + top, right - left, bottom - top


def compose(background, cam_img, mode_images, frame: Frame, boxes=(), loading=False):
    """Return a new window image: camera feed + status panel (+ face boxes)."""
    canvas = background.copy()
    canvas[CAM_Y:CAM_Y + CAM_H, CAM_X:CAM_X + CAM_W] = cam_img
    canvas[PANEL_Y:PANEL_Y + PANEL_H, PANEL_X:PANEL_X + PANEL_W] = mode_images[frame.mode]

    for box in boxes:
        canvas = cvzone.cornerRect(canvas, face_bbox(box), rt=0)
    if loading:
        cvzone.putTextRect(canvas, "Loading", (275, 400))
    if frame.mode == MODE_DETAILS and frame.employee:
        _draw_details(canvas, frame)
    return canvas


def _draw_details(canvas, frame: Frame):
    emp = frame.employee
    text = lambda key: str(emp.get(key, "-"))

    cv2.putText(canvas, text("Total_Attendance"), (861, 125), FONT, 1, WHITE, 1)
    cv2.putText(canvas, text("Occupation"), (1006, 550), FONT, 0.4, WHITE, 1)
    cv2.putText(canvas, str(frame.employee_id), (1006, 493), FONT, 0.5, WHITE, 1)
    cv2.putText(canvas, text("Employee_Standard"), (910, 625), FONT, 0.6, GREY, 1)
    cv2.putText(canvas, text("Total_Working_Years"), (1025, 625), FONT, 0.6, GREY, 1)
    cv2.putText(canvas, text("Joined_Year"), (1125, 625), FONT, 0.6, GREY, 1)

    name = text("Name")
    (w, _), _ = cv2.getTextSize(name, FONT, 1, 1)
    cv2.putText(canvas, name, (PANEL_X + (PANEL_W - w) // 2, 445), FONT, 1, DARK, 1)

    if frame.photo is not None:
        w, h = config.PHOTO_SIZE
        canvas[PHOTO_Y:PHOTO_Y + h, PHOTO_X:PHOTO_X + w] = frame.photo
