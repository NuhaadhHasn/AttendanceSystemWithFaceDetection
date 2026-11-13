"""Example: add a new employee, or update some fields of existing ones.

Edit `new_data` / `update_data`, then run this file. Only the fields listed in
`update_data` change; everything else on the record is kept.
"""
from store import init_firebase

# Records to add (leave empty to skip). Same fields as in AddData.py.
new_data = {
    # "006": {
    #     "Name": "John Doe",
    #     "Occupation": "Manager",
    #     "Joined_Year": 2023,
    #     "Total_Attendance": 10,
    #     "Last_Attendance_Time": "2023-11-03 18:04:55",
    #     "Employee_Standard": "A",
    #     "Total_Working_Years": 0
    # }
}

# Fields to update on existing records
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


def main():
    init_firebase()
    from firebase_admin import db

    ref = db.reference("Employees")
    for key, value in new_data.items():
        ref.child(key).set(value)
        print(f"Added employee {key}")
    for key, value in update_data.items():
        ref.child(key).update(value)
        print(f"Updated employee {key}: {', '.join(value)}")


if __name__ == "__main__":
    main()
