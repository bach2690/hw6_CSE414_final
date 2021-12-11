import sys
from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None
guidelines = ["Length >= 8", "Uppercase Letters", "Lowercase Letters", "Numbers", "Letters", "At least one Special Character (!, @, #, ?)"]

def password_check(pw): # Check if password follows guidelines
    length = False
    if len(pw)>=8:
        length = True
    special_characters =  ["!", "@", "#", "?"];
    num, alpha, sc, uc, lc =  False, False, False, False, False
    for char in pw:
        if char.isdigit():
            num = True
        if char.isalpha():
            alpha = True
        if char in special_characters:
            sc = True
        if char.isupper() and uc is False:
            uc = True
        if  char.islower():
            lc = True
    return [length, uc, lc, num, alpha, sc]


def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error:
        print("Error occurred when checking username")
        cm.close_connection()
    cm.close_connection()
    return False

def create_patient(tokens):
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1].lower()
    password = tokens[2]
    results = password_check(password)
    if False in results:
        print("Sorry, your password must include: ")
        for i in range(len(results)):
            print(f"{guidelines[i]}: {results[i]}")
        print("Try again!")
        return
    # check 2: check if the username has been taken already
    if username_exists_patient(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    try:
        patient = Patient(username, salt=salt, hash=hash)
        # save to caregiver information to our database
        try:
            patient.save_to_db()
        except:
            print("Create failed, Cannot save")
            return
        print(" *** Account created successfully *** ")
    except pymssql.Error:
        print("Create failed")
        return
    pass


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1].lower()
    password = tokens[2]
    results = password_check(password)
    if False in results:
        print("Sorry, your password must include: ")
        for i in range(len(results)):
            print(f"{gl[i]}: {results[i]}")
        print("Try again!")
        return
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    try:
        caregiver = Caregiver(username, salt=salt, hash=hash)
        # save to caregiver information to our database
        try:
            caregiver.save_to_db()
        except:
            print("Create failed, Cannot save")
            return
        print(" *** Account created successfully *** ")
    except pymssql.Error:
        print("Create failed")
        return


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error:
        print("Error occurred when checking username")
        cm.close_connection()
    cm.close_connection()
    return False


def login_patient(tokens):
    global current_patient, current_caregiver
    if current_patient is not None or current_caregiver is not None:
        print("Already logged-in!")
        return

    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1].lower()
    password = tokens[2]

    patient = None
    try:
        try:
            patient = Patient(username, password=password).get()
        except:
            print("Get Failed")
            return
    except pymssql.Error:
        print("Error occurred when logging in")

    # check if the login was successful
    if patient is None:
        print("Please try again!")
    else:
        print("Patient logged in as: " + username)
        current_patient = patient
    pass


def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("Already logged-in!")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1].lower()
    password = tokens[2]

    caregiver = None
    try:
        try:
            caregiver = Caregiver(username, password=password).get()
        except:
            print("Get Failed")
            return
    except pymssql.Error:
        print("Error occurred when logging in")

    # check if the login was successful
    if caregiver is None:
        print("Please try again!")
    else:
        print("Caregiver logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    if len(tokens) != 2:
        print("Please try again!")
        return
    date = tokens[1]
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        try:
            print("Available caregivers: ")
            cursor.execute("SELECT C.Username FROM Caregivers AS C JOIN Availabilities AS A ON C.Username=A.Username WHERE A.Time=%d GROUP BY C.Username", d)
            row = cursor.fetchone()
            if row is None:
                print("No available caregivers on this date!")
            while row is not None:
                print(row)
                row = cursor.fetchone()
            print("Available vaccines: ")
            cursor.execute("SELECT V.Name, SUM(V.doses) FROM Vaccines AS V GROUP BY V.Name")
            row = cursor.fetchone()
            if row is None:
                print("No available vaccine doses!")
            while row is not None:
                print(row)
                row = cursor.fetchone()
        except:
            print("Schedule Search Failed!")
    except ValueError:
        print("Please enter a valid date!")
    except pymssql.Error as db_err:
        print("Error occurred when searching for schedule")
        cm.close_connection()
    cm.close_connection()

def reservation_check(pt, date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Appointments WHERE Time=%s AND Patient_Username=%s", (date, pt))
    row = cursor.fetchone()
    cm.close_connection()
    if row is None:
        return False
    return True

def reserve(tokens):
    global current_patient
    if current_patient is None:
        print("Please login as a patient first!")
        return
    if len(tokens) != 3:
        print("Please try again!")
        return
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    vaccine = str(tokens[2].lower())
    date = tokens[1]
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        try:
            if reservation_check(current_patient.username, d):
                print("Sorry, you already have a reservation on that date!")
                return
            cursor.execute("SELECT A.Username FROM Availabilities AS A WHERE A.Time = %d ORDER BY RAND()", d)
            assigned_caregiver = cursor.fetchone()
            if assigned_caregiver is None:
                print("No available appointments on that date!")
                return
            cursor.execute("SELECT V.Doses FROM Vaccines AS V WHERE V.Name=%s", vaccine)
            doses_left = cursor.fetchone()
            if int(doses_left[0]) <=0:
                print("No doses of that vaccine left!")
                return
            cursor.execute("INSERT INTO Appointments VALUES (%s, %s, %s, %s)", (current_patient.username, assigned_caregiver[0], vaccine, d))
            cursor.execute("DELETE FROM Availabilities WHERE Username=%s AND Time=%s", (assigned_caregiver[0], d))
            cursor.execute("UPDATE Vaccines SET Doses = Doses-1 WHERE name = %s", vaccine)
            conn.commit()
            cursor.execute("SELECT Ap.Appt_id FROM Appointments AS Ap WHERE Ap.Time=%d", d)
            row = cursor.fetchone()
            print("Assigned Caregiver: ", assigned_caregiver[0])
            print("Appointment ID: ", row[0])
        except:
            print("Reservation Failed!")
    except ValueError:
        print("Please enter a valid date!")
    except pymssql.Error as db_err:
        print("Error occurred with reservation system")
        cm.close_connection()
    cm.close_connection()


def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        try:
            current_caregiver.upload_availability(d)
        except:
            print("Upload Availability Failed")
        print("Availability uploaded!")
    except ValueError:
        print("Please enter a valid date!")
    except pymssql.Error as db_err:
        print("Error occurred when uploading availability")


def cancel(tokens):
    if current_patient is None and current_caregiver is None:
        print("Please login first!")
        return
    if len(tokens) != 2:
        print("Please try again!")
        return
    aid = int(tokens[1])
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    try:
        try:
            print("H!!!!!")
            cursor.execute("SELECT * FROM Appointments AS A WHERE A.Appt_id = %d", int(aid))
            row = cursor.fetchone()
            if row is None:
                print("No such appointment!")
                return
            pt = row[1]
            cg = row[2]
            if pt!=current_patient.username and cg!=current_caregiver.username:
                print("Sorry, you can only cancel your own appointment!")
                return
            vc = row[3]
            dt = row[4]
            print("F123!!!!!")
            cursor.execute("DELETE FROM Appointments WHERE Appt_id = %d", int(aid))
            cursor.execute("INSERT INTO Availabilities VALUES (%s, %s)", (dt, cg))
            cursor.execute("UPDATE Vaccines SET Doses = Doses+1 WHERE name = %s", vc)
            conn.commit()
            print("Successfully cancelled!")
        except:
            print("Cancellation Failed!")
    except ValueError:
        print("Please enter a valid Appointment ID!")
    except pymssql.Error as db_err:
        print("Error occurred with reservation system")
        cm.close_connection()
    cm.close_connection()


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = str(tokens[1].lower())
    doses = int(tokens[2])
    vaccine = None
    try:
        try:
            vaccine = Vaccine(vaccine_name, doses).get()
        except:
            print("Failed to get Vaccine!")
            return
    except pymssql.Error:
        print("Error occurred when adding doses")

    # check 3: if getter returns null, it means that we need to create the vaccine and insert it into the Vaccines
    #          table

    if vaccine is None:
        try:
            vaccine = Vaccine(vaccine_name, doses)
            try:
                vaccine.save_to_db()
            except:
                print("Failed To Save")
                return
        except pymssql.Error:
            print("Error occurred when adding doses")
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            try:
                vaccine.increase_available_doses(doses)
            except:
                print("Failed to increase available doses!")
                return
        except pymssql.Error:
            print("Error occurred when adding doses")

    print("Doses updated!")


def show_appointments(tokens):
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first!")
        return
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    try:
        if current_caregiver is not None:
            cursor.execute("SELECT Ap.Appt_id,Ap.Vaccine_name,Ap.Time,Ap.Patient_Username FROM Appointments AS Ap WHERE Ap.Caregiver_Username=%s", current_caregiver.username)
            row = cursor.fetchone()
            if row is None:
                print("You have no appointments.")
                return
            while row is not None:
                print(f"Appointment ID: {row[0]}, Vaccine name: {row[1]}, Time: {str(row[2])}, Patient: {row[3]}")
                row = cursor.fetchone()
        elif current_patient is not None:
            cursor.execute("SELECT Ap.Appt_id,Ap.Vaccine_name,Ap.Time,Ap.Caregiver_Username FROM Appointments AS Ap WHERE Ap.Patient_Username=%s", current_patient.username)
            row = cursor.fetchone()
            if row is None:
                print("You have no appointments.")
                return
            while row is not None:
                print(f"Appointment ID: {row[0]}, Vaccine name: {row[1]}, Time: {str(row[2])}, Caregiver: {row[3]}")
                row = cursor.fetchone()
    except pymssql.Error as db_err:
        print("Error occurred when uploading availability")
        cm.close_connection()
    cm.close_connection()



def logout(tokens):
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("No one is logged in!")
        return
    elif current_patient is not None:
        current_patient = None
    elif current_caregiver is not None:
        current_caregiver=None
    print("Successfully logged out! 1234")


def start():
    stop = False
    while not stop:
        print()
        print(" *** Please enter one of the following commands *** ")
        print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
        print("> create_caregiver <username> <password>")
        print("> login_patient <username> <password>")  #// TODO: implement login_patient (Part 1)
        print("> login_caregiver <username> <password>")
        print("> search_caregiver_schedule <date>")  #// TODO: implement search_caregiver_schedule (Part 2)
        print("> reserve <date> <vaccine>") #// TODO: implement reserve (Part 2)
        print("> upload_availability <date>")
        print("> cancel <appointment_id>") #// TODO: implement cancel (extra credit)
        print("> add_doses <vaccine> <number>")
        print("> show_appointments")  #// TODO: implement show_appointments (Part 2)
        print("> logout") #// TODO: implement logout (Part 2)
        print("> Quit")
        print()
        response = ""
        print("> Enter: ", end=' ')

        try:
            response = str(input())
        except ValueError:
            print("Type in a valid argument")
            break

        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Try Again")
            continue
        operation = tokens[0].lower()
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == "cancel":
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Thank you for using the scheduler, Goodbye!")
            stop = True
        else:
            print("Invalid Argument")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
