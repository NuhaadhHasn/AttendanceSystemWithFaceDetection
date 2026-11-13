import os
import pickle
import cvzone
import numpy as np
import cv2
from datetime import datetime
import face_recognition

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://attendancewithfacerecogn-5cfbb-default-rtdb.firebaseio.com/',
    'storageBucket': 'attendancewithfacerecogn-5cfbb.appspot.com'
})

bucket = storage.bucket()

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

imgBackground = cv2.imread('Resources/background.png')

# Importing Mode images into a list
modePath = 'Resources/Modes'
modePathList = os.listdir(modePath)
modeImgLists = []
for path in modePathList:
    modeImgLists.append(cv2.imread(os.path.join(modePath, path)))

# Load the encoding file
print("Loading Encoded File ...")
file = open("EncodeFile.p", 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, employeeId = encodeListKnownWithIds
print("Encoded File Loaded Successfully")

modeType = 0
counter = 0
id = -1
imgEmployee = []

while True:
    success, img = cap.read()

    # making the image smaller, to make the process faster
    imgSmall = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    # saving the face from cam in rgb, so it works in the face recognition
    imgSmall = cv2.cvtColor(imgSmall, cv2.COLOR_BGR2RGB)

    faceCurFrame = face_recognition.face_locations(imgSmall)
    encodeCurFrame = face_recognition.face_encodings(imgSmall, faceCurFrame)

    imgBackground[162:162 + 480, 55:55 + 640] = img
    imgBackground[44:44 + 633, 808:808 + 414] = modeImgLists[modeType]

    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown,
                                                     encodeFace)  # finding true or false of matching faces
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)  # finding the least index
            print(f"Matches :{matches}")
            print(f"FaceDis :{faceDis}")

            matchIndex = np.argmin(faceDis)  # get index of the matching face from the list
            # print(f"Match Index {matchIndex}")
            if matches[matchIndex]:
                # print("Know Face Detected")
                # print(employeeId[matchIndex])
                y1, x2, y2, x1 = faceLoc  # to get the mark around the face
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4  # getting back default size after we made it smaller
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                # imgBackground = cv2.rectangle(imgBackground,(y1,x1), (y1+ x2, y2+ x1), (255, 0, 0), 2 )

                id = employeeId[matchIndex]
                # print(id)

                if counter == 0:
                    cvzone.putTextRect(imgBackground, "Loading", (275,400))
                    cv2.imshow("Attendance With Face Recognition", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1

        if counter != 0:

            if counter == 1:
                # Get Employee Data
                employeeInfo = db.reference(f'Employees/{id}').get()
                print(employeeInfo)
                # Get the image from the db
                blob = bucket.get_blob(f'Images/{id}.png')
                testTring = blob.download_as_string()
                array = np.frombuffer(blob.download_as_string(), np.uint8)
                imgEmployee = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)
                # Mark Attendance
                datetimeObject = datetime.strptime(employeeInfo['Last_Attendance_Time'],
                                                   "%Y-%m-%d %H:%M:%S")
                secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                print(secondsElapsed)
                # if secondsElapsed > 86400: # Update after 24 hours of last update
                if secondsElapsed > 30:  # Update after 30 seconds of last update
                    ref = db.reference(f'Employees/{id}')
                    employeeInfo['Total_Attendance'] += 1
                    ref.child('Total_Attendance').set(employeeInfo['Total_Attendance'])
                    ref.child('Last_Attendance_Time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    modeType = 3
                    counter = 0
                    imgBackground[44:44 + 633, 808:808 + 414] = modeImgLists[modeType]

            if modeType != 3:

                if 10 < counter < 20:
                    modeType = 2

                imgBackground[44:44 + 633, 808:808 + 414] = modeImgLists[modeType]

                if counter <= 10:
                    # Replacing the data from the interface
                    cv2.putText(imgBackground, str(employeeInfo['Total_Attendance']), (861, 125),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(employeeInfo['Occupation']), (1006, 550),
                                cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(id), (1006, 493),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(employeeInfo['Employee_Standard']), (910, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(employeeInfo['Total_Working_Years']), (1025, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(employeeInfo['Joined_Year']), (1125, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    (w, h), _ = cv2.getTextSize(employeeInfo['Name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2

                    cv2.putText(imgBackground, str(employeeInfo['Name']), (808 + offset, 445),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    imgBackground[175:175 + 216, 909:909 + 216] = imgEmployee

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    employeeInfo = []
                    imgEmployee = []
                    imgBackground[44:44 + 633, 808:808 + 414] = modeImgLists[modeType]

    else:
        modeType = 0
        counter = 0

    # cv2.imshow("Webcam", img)
    cv2.imshow("Attendance With Face Recognition", imgBackground)
    cv2.waitKey(1)
