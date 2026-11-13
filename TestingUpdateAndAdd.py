import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://attendancewithfacerecogn-5cfbb-default-rtdb.firebaseio.com/'
})

ref = db.reference('Employees')

# Add new data to the database
# new_data = {
#     "006": {
#         "Name": "John Doe",
#         "Occupation" : "Manager",
#         "Joined_Year": 2023,
#         "Total_Attendance": 10,
#         "Last_Attendance_Time": "2023-11-03 18:04:55",
#         "Employee_Standard": "A",
#         "Total_Working_Years": 0
#     }
# }

# Update existing data in the database
update_data = {
    "001": {
        "Total_Attendance": 55,
        "Total_Working_Years": 3
    },
    "002": {
        "Total_Attendance": 10,
        "Total_Working_Years": 1
    }
}

# Add new data to the database
# for key, value in new_data.items():
#     ref.child(key).set(value)

# Update existing data in the database
for key, value in update_data.items():
    ref.child(key).update(value)
