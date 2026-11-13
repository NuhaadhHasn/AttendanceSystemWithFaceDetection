import cv2
import os
import face_recognition
import pickle


import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://attendancewithfacerecogn-5cfbb-default-rtdb.firebaseio.com/',
    'storageBucket': 'attendancewithfacerecogn-5cfbb.appspot.com'
})

# Importing Employee images
imgPath = 'Images/'
imgPathList = os.listdir(imgPath)
imgLists = []
employeeId = []
for path in imgPathList:
    imgLists.append(cv2.imread(os.path.join(imgPath, path)))
    print(imgLists)
    employeeId.append(os.path.splitext(path)[0])
    fileName =os.path.join(imgPath, path)
    bucket = storage.bucket()
    blob = bucket.blob(fileName)
    blob.upload_from_filename(fileName)


def find_encodings(image_lists):
    encode_list = []
    for img in image_lists:
        # saving the file in rgb so it works in the face recognition
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encode_list.append(encode)

    return encode_list


print("Encoding Started...")
encodeListKnown = find_encodings(imgLists)
encodeListKnownWithIds = (encodeListKnown, employeeId)
print(f"encodeListKnownWithIds : {encodeListKnownWithIds}")
print("Encoding Completed")

file = open("EncodeFile.p", 'wb')
pickle.dump(encodeListKnownWithIds, file)
file.close()
print("File Saved")