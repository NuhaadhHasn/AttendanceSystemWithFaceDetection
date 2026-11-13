import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://attendancewithfacerecogn-5cfbb-default-rtdb.firebaseio.com/'
})

ref = db.reference('Employees')

data = {
    "001": {
        "Name": "Nuhaadh Hassan",
        "Occupation" : "Software Engineer",
        "Joined_Year": 2021,
        "Total_Attendance": 50,
        "Last_Attendance_Time": "2023-10-11 18:04:55",
        "Employee_Standard": "G",
        "Total_Working_Years": 2
    },
    "002": {
        "Name": "Emily Blunt",
        "Occupation" : "Actress",
        "Joined_Year": 2021,
        "Total_Attendance": 5,
        "Last_Attendance_Time": "2023-10-11 18:04:55",
        "Employee_Standard": "G",
        "Total_Working_Years": 2
    },
    "003": {
        "Name": "Elon Musk",
        "Occupation" : "Entrepreneur",
        "Joined_Year": 2021,
        "Total_Attendance": 7,
        "Last_Attendance_Time": "2023-10-11 18:04:55",
        "Employee_Standard": "G",
        "Total_Working_Years": 2
    },
    "004": {
        "Name": "Abed Ahmed",
        "Occupation" : "Software Engineer",
        "Joined_Year": 2023,
        "Total_Attendance": 30,
        "Last_Attendance_Time": "2023-10-11 18:04:55",
        "Employee_Standard": "B",
        "Total_Working_Years": 0
    },
    "005": {
        "Name": "Shakeer Ahmed",
        "Occupation" : "Network Engineer",
        "Joined_Year": 2018,
        "Total_Attendance": 20,
        "Last_Attendance_Time": "2023-10-03 18:04:55",
        "Employee_Standard": "VB",
        "Total_Working_Years": 5
    },
}

# Add new Record
for key,value in data.items():
    ref.child(key).set(value)

# if you need to update records, you can use the below code
# for key, value in data.items():
#     ref.child(key).update(value)