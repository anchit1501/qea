# read all employee details into a list

import os
import csv 
    
# field names 
fields = ['first name', 'middle name', 'surname', 'email']    

EMPLOYEE_DB = []


class Employee():

    def __init__(self):
        self.first_name = None
        self.surname = None
        self.middle_name = None
        self.email = None

    def get_first_name(self):
        return self.first_name

    def get_surname(self):
        return self.surname

    def get_middle_name(self):
        return self.middle_name
    
    def get_email(self):
        return self.email

    def set_first_name(self, employee_first_name):
        self.first_name = employee_first_name

    def set_surname(self, employee_surname):
        self.surname = employee_surname

    def set_middle_name(self, employee_middle_name):
        self.middle_name = employee_middle_name

    def set_email(self, employee_email):
        self.email = employee_email



# create a employee file
file = "employee_records.csv"
with open(file, 'a+') as csvfile:
    
    csvwriter = csv.writer(csvfile) 
                    
    # writing the fields 
    csvwriter.writerow(fields) 

    with open("employee_records.txt", 'r') as a_file:
        
        for line in a_file:

            key, value = line.strip().split(',')
            
            name = key.split()
            # print(name)
            # print(value)

            if len(name) == 2:
                row = [name[0], "None", name[1], value]
            else:
                row = [name[0], name[1], name[2], value]
            # writing the data rows 
            csvwriter.writerow(row)

            
EMPLOYEE_DB = []

with open('employee_records.csv') as a_file:

    for line in a_file:
        x = line.rstrip('\n').split(",")
        if len(x)!=1: 
            print(x)
            employee = Employee()
            employee.set_first_name(x[0])
            employee.set_email(x[3])
            employee.set_middle_name(x[1])
            employee.set_surname(x[2])
            EMPLOYEE_DB.append(employee)

print("Length of Employee DB", len(EMPLOYEE_DB))


name = "Bharti"
name_list=[]
for employee in EMPLOYEE_DB:
    print("first name: ", employee.get_first_name())
    if name.lower() == employee.get_first_name():
        print("IN")
        name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
        # email = employee.get_email()
    print("name_list: ", name_list)

if len(name_list) > 1:
    # there are two employees with same name
    # surnames = []
    textt = "Do you want to know about "
    for name in name_list:
        # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
        textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
    textt = textt[:-5] + "?"
    print(textt)
elif len(name_list) == 1:
    # there is only one employee with the name
    email = name_list[0][0]
    print("print email ", email)
elif len(name_list) == 0:
    print("The employee does not exist.")
    # return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]