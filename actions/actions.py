# @author: Bharti Sanjeebkumar Sinha, Analyst @Intellificial
# Developed for Intellificial's Enterprise HelpDesk

from tracemalloc import start
from typing import Any, Text, Dict, List
from requests.exceptions import HTTPError
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset
import itertools

from datetime import datetime as dt
from datetime import date as datepkg
# from dateutil import tz

#for connecting to Microsoft Outlook
#https://o365.github.io/python-o365/latest/index.html 
# from O365.connection import Connection
from O365 import Account, MSGraphProtocol
# from O365 import address_book

# to store conversations, detected intents and bot responses 
import csv 

#Miscellaneous
import warnings
import os.path

#ignore warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.simplefilter('ignore')


global account
global calendar
# Outlook credentials, as per Azure Active Directory, 'Calendar' app registered via qea's intellificial account
CLIENT_ID = '28b64d34-d1a6-424c-9f24-94f281d65b22'
SECRET_ID = 'U-88Q~HT2b30UMH~3dT9gI6Ig.CUtos2OEeiFbFO'
credentials = (CLIENT_ID, SECRET_ID)
protocol = MSGraphProtocol() 
scopes = ['Calendars.Read.Shared', 'User.ReadBasic.All', 'Contacts.Read', 'Directory.Read.All', "offline_access"]

ACCOUNT = Account(credentials, protocol=protocol)
if ACCOUNT.authenticate(scopes=scopes, offline_access=True):
    print('Authenticated!')

# connect = Connection(credentials, scopes=scopes)
# connect.refresh_token()

SLOTS_FILLED =["time", "name", "employee"]

# to store mappings between month number and month name
# global month_dict
MONTH_DICT = {1:'January', 2:'February', 
            3:'March', 4:'April', 5:'May', 
            6:'June', 7:'July', 8:'August', 
            9:'Septempber', 10:'October', 
            11:'November', 12:'December'}

# month numbers in list with respoective number of days
THIRTY_ONE_DAYS =[1, 3, 5, 7, 8, 10, 12]
THIRTY_DAYS =[4, 6, 9, 11]

#to add suffix as "th", "rd", "st" and "nd"
ST=[1, 21,31]
ND=[2, 22]
RD=[3, 23]
TH=[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29, 30]

file = "employee_records.csv"
fields_employee = ['first name', 'middle name', 'surname', 'email'] 

if not os.path.isfile("employee_records.csv"):
    with open(file, 'a+') as csvfile:

        csvwriter1 = csv.writer(csvfile) 
                        
        # writing the fields 
        csvwriter1.writerow(fields_employee) 

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
                csvwriter1.writerow(row)

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


# read all employee details into a list
global EMPLOYEE_DB
EMPLOYEE_DB = []

with open('employee_records.csv') as a_file:

    for line in a_file:
        x = line.rstrip('\n').split(",")
        if len(x)!=1: 
            # print(x)
            employee = Employee()
            employee.set_first_name(x[0])
            employee.set_email(x[3])
            employee.set_middle_name(x[1])
            employee.set_surname(x[2])
            EMPLOYEE_DB.append(employee)

print("Length of Employee DB", len(EMPLOYEE_DB))

class StoreConversations():
    """This class create a csv file named
        'qea_records.csv'. 
        If the file does not exist, then it's created and field names are added,
        Else, the file is opened and row is added for each conversations.
    """

    def __init__(self):
        # field names 
        self.fields = ['User Name', 'Utterance', 'Detected Intent', 'Response', 'Entities', 'Enquired about Employee'] 
        # name of csv file 
        self.filename = "qea_records.csv"
    
    def run_once(self):
        # writing to csv file 
        with open(self.filename, 'a+') as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile)   
            # writing the fields 
            csvwriter.writerow(self.fields) 

        print("======================")
        print("{} created.".format(self.filename))
        print("======================")
        print("\n")
       
    def run(self, row):
        with open(self.filename, 'a+') as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(row)

# STORE DATA
STORE = StoreConversations()
if not os.path.isfile("qea_records.csv"):
    STORE.run_once()

# util class
class PrintBasicInfo():

    def __init__(self, tracker):
        self.tracker = tracker
    
    def run(self):
        print("user message: ", self.tracker.latest_message["text"])  
        print("detected intent: ", self.tracker.latest_message["intent"])
        print("\n") 

#get the username and email id of the employee who is asking questions to qea
class ActionCheckUserInfo(Action):

    def name(self) -> Text:
        return "action_check_user_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_information_str = tracker.sender_id
        user_information_str_dict = eval(user_information_str) 
        username = user_information_str_dict.get("name") 
        email = user_information_str_dict.get("email") 

        return username, email

class HandleTime():

    def __init__(self, time, range_):
        self.time = time
        self.range_ = range_
    
    def get_time_from_duckling(self):
        print("Detected time: ", self.time)
        if not self.range_:
            format = "%Y-%m-%dT%H:%M:%S.%f%z"
            date = dt.strptime(self.time, format).date()
            date = str(date)
            date = date.split("-")
            print("DATE WHEN NOT RANGE: ", date)
            return date
        else:
            from_datetime = self.time["from"]
            to_datetime = self.time["to"]
            format = "%Y-%m-%dT%H:%M:%S.%f%z"
            from_time = dt.strptime(from_datetime, format).time()
            to_time = dt.strptime(to_datetime, format).time()
            date = dt.strptime(from_datetime, format).date()
            date = str(date)
            date = date.split("-")
            print("DATE WHEN IN RANGE: ", date)
            print("extra, from and to time:  ", from_time, to_time)
            print("-------------------------------------")
            return from_time, to_time, date


class GetCalendar():

    def __init__(self, email, date):
        self.email = email
        self.date = date

    def get_calendar(self):

        schedule = ACCOUNT.schedule(resource=self.email)
        try: 
            calendar = schedule.get_default_calendar()
        except HTTPError as e:
            print("Exception: ", e)
            return "The employee has not shared their calendar yet."
            # return "Nill"

        # if month is not feb
        if int(self.date[1]) !=2: 

            # if the month has 31 days
            if int(self.date[2]) == 31 and (int(self.date[1]) in THIRTY_ONE_DAYS):
                q = calendar.new_query('start').greater_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])))
                q.chain('and').on_attribute('end').less_equal(dt(int(self.date[0]), int(self.date[1])+1, 1))
                all_events = calendar.get_events(query=q, include_recurring=True)  
            # if the month has 30 days
            elif int(self.date[2]) == 30 and (int(self.date[1]) in THIRTY_DAYS):
                q = calendar.new_query('start').greater_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])))
                q.chain('and').on_attribute('end').less_equal(dt(int(self.date[0]), int(self.date[1])+1, 1))
                all_events = calendar.get_events(query=q, include_recurring=True)  
            # if the day is any other than the end of the month
            else:
                q = calendar.new_query('start').greater_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])))
                q.chain('and').on_attribute('end').less_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])+1))
                all_events = calendar.get_events(query=q, include_recurring=True) 
        
        # for the month of February
        else:
            if int(self.date[2]) == 28:
                q = calendar.new_query('start').greater_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])))
                q.chain('and').on_attribute('end').less_equal(dt(int(self.date[0]), int(self.date[1])+1, 1))
                all_events = calendar.get_events(query=q, include_recurring=True) 
            else:
                q = calendar.new_query('start').greater_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])))
                q.chain('and').on_attribute('end').less_equal(dt(int(self.date[0]), int(self.date[1]), int(self.date[2])+1))
                all_events = calendar.get_events(query=q, include_recurring=True) 

        return all_events

    def get_suffix(self):

        if int(self.date[2]) in ST:
            return "st"
        elif int(self.date[2]) in ND:
            return "nd"
        elif int(self.date[2]) in RD:
            return "rd"
        else:
            return "th"

class Response():

    def __init__(self, all_events, date, tracker, my_calendar, from_time=None, to_time=None, range=False, name=None):
        self.events = all_events
        self.date = date
        self.tracker = tracker
        self.my_calendar = my_calendar
        self.from_time = from_time
        self.to_time = to_time
        self.range = range
        self.name = name

    def get_date_user_asked(self):

        user_day = ""
        temp=[]
        for dicti in self.tracker.current_state()["events"]:
            if dicti["event"] == "user":
                # print("------------------------")
                # print(dicti)
                # print("------------------------")
                try:
                    if self.name == None: 
                        temp.append(dicti["parse_data"]["entities"][0]["text"])
                    else:
                        temp.append(dicti["parse_data"]["entities"][1]["text"])
                except Exception as e:
                    continue
        if len(temp) !=0:
            user_day = temp[-1]
            return user_day


    def prettyPrinter(self):
        
        print("NAME", self.name)
        user_day = self.get_date_user_asked()
        print("USER DAY", user_day)
        print(type(user_day))
        month_asked = MONTH_DICT[int(self.date[1])]

        suffix = self.my_calendar.get_suffix()
        
        meetings =""

        if not self.range:
            time_stamps_start=[]
            for event in self.events:

                subject = event.subject
                if subject[:9] =="Canceled:":
                    continue

                start_time = event.start
                # print("without range start time 1: ", start_time)

                end_time = event.end
                # print("without range end time 1: ", end_time)

                start_time = start_time.time().strftime('%H:%M') 
                # print("without range start time 2: ", start_time)

                end_time = end_time.time().strftime('%H:%M') 
                # print("without range end time 2: ", end_time)


                # add start time, end time and subject as a tuple to a list, 
                # this will be sorted based on start date at the end of the loop

                # avoid duplicate meetings
                if not (subject in itertools.chain(*time_stamps_start)):
                    time_stamps_start.append((start_time, end_time, subject))

            # sort the list of start time 
            # if two meetings have same start time, pick a random one to display
            # print("without range time stamps before: ", time_stamps_start)
            time_stamps_start.sort(key=lambda a: a[0])
            # print("without range time stamps after:", time_stamps_start)
            meetings = ""
            if len(time_stamps_start)==0:
                if self.name==None and user_day!=None:
                    meetings = "You don't have any planned meetings {} 😊".format(user_day)
                    # if "on" not in user_day and () and : 
                    #     meetings = "You don't have any planned meetings on {} 😊".format(user_day)
                    # else:
                    #     meetings = "You don't have any planned meetings {} 😊".format(user_day)
                    print(meetings)
                    return meetings
                elif self.name==None and user_day==None:
                    print(" here 1")
                    meetings = "You don't have any planned meetings 😊"
                    # if "on" not in user_day and () and : 
                    #     meetings = "You don't have any planned meetings on {} 😊".format(user_day)
                    # else:
                    #     meetings = "You don't have any planned meetings {} 😊".format(user_day)
                    print(meetings)
                    return meetings
                elif self.name!=None and user_day==None:
                    print(" here 2")
                    meetings = "{} doesn't have any planned meetings 😊".format(self.name.capitalize())
                    # if "on" not in user_day and () and : 
                    #     meetings = "You don't have any planned meetings on {} 😊".format(user_day)
                    # else:
                    #     meetings = "You don't have any planned meetings {} 😊".format(user_day)
                    print(meetings)
                    return meetings
                else:
                    meetings = "{} doesn't have any planned meetings {} 😊".format(self.name.capitalize(), user_day)
                    # if "on" not in user_day: 
                    #     meetings = "{} doesn't have any planned meetings on {} 😊".format(self.name.capitalize(), user_day)
                    # else:
                    #     meetings = "{} doesn't have any planned meetings {} 😊".format(self.name.capitalize(), user_day)
                    print(meetings)
                    return meetings

            else:
                if self.name == None: 
                    meetings ="Your meetings on {}{} {} {}:".format(int(self.date[2]), suffix, month_asked, int(self.date[0]))
                    meetings = meetings + "\n"
                else:
                    meetings ="{}'s meetings on {}{} {} {}:".format(self.name.capitalize(), int(self.date[2]), suffix, month_asked, int(self.date[0]))
                    meetings = meetings + "\n"

                count = 1
                for t in time_stamps_start:
                    start_time = dt.strptime(t[0], "%H:%M")
                    start_time = start_time.strftime("%I:%M %p")
                    end_time = dt.strptime(t[1], "%H:%M")
                    end_time = end_time.strftime("%I:%M %p")
                    meetings = meetings + "{}. {}: {} to {}\n".format(count ,t[2], str(start_time), str(end_time))   
                    count = count +1 

            print(meetings)
            return meetings
        else:  
            # list_subjects=[]
            counter =1 
            time_stamps = []
            if self.name == None: 
                meetings ="Your meetings on {}{} {} {}:\n".format(int(self.date[2]), suffix, month_asked, int(self.date[0]))
                # meetings = meetings + "\n"
            else:
                meetings ="{}'s meetings on {}{} {} {}:\n".format(self.name.capitalize(), int(self.date[2]), suffix, month_asked, int(self.date[0]))
                # meetings = meetings + "\n"

            for event in self.events:
                
                subject = event.subject
                if subject[:9] =="Canceled:":
                    continue
                # print("current subject: ", subject)
            
                start_time = event.start
                # print("start time 1: ", start_time)
                meeting_start= start_time.time()
                # print("meeting start 2: ", meeting_start)
                start_time_ = start_time.time().strftime('%H:%M')
                # print("start time 3: ", start_time_)
                # start_time_ = dt.strptime(start_time_, "%H:%M")
                # print("start time 4: ", start_time_)
                # start_time_ = start_time_.strftime("%I:%M %p")
                # print("start time 5: ", start_time_)

                end_time = event.end
                # print("end time 1: ", end_time)
                meeting_end= end_time.time()
                # print("meeting end time 1: ", meeting_end)
                end_time_ = end_time.time().strftime('%H:%M')
                # print("end time 1: ", end_time_)
                # end_time_ = dt.strptime(end_time_, "%H:%M")
                # print("end time 1: ", end_time_)
                # end_time_ = end_time_.strftime("%I:%M %p")
                # print("end time 1: ", end_time_)


                # add only those meetings that are in the range

                if meeting_start >= self.from_time and meeting_start <= self.to_time:
                    # avoid duplicate meetings
                    if not (subject in itertools.chain(*time_stamps)):
                        time_stamps.append((start_time_, end_time_, subject))
                    counter = counter+1
            # print("time stamps before sorting: ", time_stamps)
            time_stamps.sort(key=lambda a: a[0])
            # print("time stamps after sorting: ", time_stamps)


            count = 1
            for start, end, sub in time_stamps:
                start_time_ = dt.strptime(start, "%H:%M")
                # print("start time 4: ", start_time)
                start_time_ = start_time_.strftime("%I:%M %p")
                # print("start time 5: ", start_time_)

                end_time_ = dt.strptime(end, "%H:%M")
                # print("end time 4: ", end_time_)
                end_time_ = end_time_.strftime("%I:%M %p")
                # print("end time 5: ", end_time_)

                test = "{}. {}: {} to {}\n".format(count, sub, str(start_time_), str(end_time_))
                meetings = meetings + test
                count = count + 1

            # print("counter: ", counter)
            if counter==1:
                if self.name == None and user_day!=None: 
                    # print(" here 3")
                    # print(user_day)
                    meetings = "You don't have any planned meetings {} 😊".format(user_day)
                    # if "on" not in user_day: 
                    #     meetings = "You don't have any planned meetings on {} 😊".format(user_day)
                    # else:
                    #     meetings = "You don't have any planned meetings {} 😊".format(user_day)
                elif self.name == None and user_day==None: 
                    # print(user_day)
                    meetings = "You don't have any planned meetings 😊".format(user_day)
                elif self.name != None and user_day==None: 
                    # print(" here 4")
                    # print(user_day)
                    meetings = "{} doesn't have any planned meetings 😊".format(self.name.capitalize())
                elif self.name != None and user_day!=None:
                    # print(" here 5")
                    meetings = "{} doesn't have any planned meetings {} 😊".format(self.name.capitalize(), user_day)
                    # if "on" not in user_day: 
                    #     meetings = "{} doesn't have any planned meetings on {} 😊".format(self.name.capitalize(), user_day)
                    # else:
                    #     meetings = "{} doesn't have any planned meetings {} 😊".format(self.name.capitalize(), user_day)
                else:
                    print("ERROR")
            print(meetings)
            return meetings
                        

                    
# this class handles when an employee asks about their personal calender 
# and clearly mentions the day they want the information for
class ActionPersonalSchedule(Action):

    def name(self) -> Text:
        return "action_personal_schedule"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        printt = PrintBasicInfo(tracker)
        printt.run()   

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name) )
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        # get date and time as per user utterance
        time = tracker.get_slot("time")
        handle_time = HandleTime(time, range_=False)
        date_and_time = handle_time.get_time_from_duckling()
        print("date_and_time: ",date_and_time)

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        row = [username, tracker.latest_message["text"], tracker.latest_message["intent"], "action_personal_schedule", slot_value_temp, "self"]
        STORE.run(row)

        # get the associated calender
        my_calendar = GetCalendar(email, date_and_time)
        all_events = my_calendar.get_calendar()

        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date_and_time, tracker, my_calendar, from_time=None, to_time=None, range=False)
            meetings = response.prettyPrinter()
        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)

        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        # return[AllSlotsReset()]
        

        
# this class handles situation when an employee asks for personal calendar
# without mentioning the time or day
# it assumes, the concerned day is current date
class ActionPersonalScheduleAmbiguous(Action):

    def name(self) -> Text:
        return "action_personal_schedule_ambiguous"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                "self"]

        STORE.run(row)

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()

        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time=None, to_time=None, range=False)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]


class ActionRangeWeirdPersonal(Action):

    def name(self) -> Text:
        return "action_range_weird_personal"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        if "afternoon" in tracker.latest_message['text'] or "aftrnoon" in tracker.latest_message['text'] or "noon" in tracker.latest_message['text']:
            datetime_str_from = "24AUG2001120000"
            datetime_str_to = "24AUG2001190000"

            datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
            datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

            from_time = datetime_obj_from.time()
            to_time = datetime_obj_to.time()

        elif "morning" in tracker.latest_message['text'] or "mrng" in tracker.latest_message['text'] :
            datetime_str_from = "24AUG2001000000"
            datetime_str_to = "24AUG2001120000"
            datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
            datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

            from_time = datetime_obj_from.time()
            to_time = datetime_obj_to.time()
        
        elif "evening" in tracker.latest_message['text'] or "evng" in tracker.latest_message['text']:
           datetime_str_from = "24AUG2001190000"
           datetime_str_to = "24AUG2001000000"
           datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
           datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")
           from_time = datetime_obj_from.time()
           to_time = datetime_obj_to.time()

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                "self"]

        STORE.run(row)

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True)
            meetings = response.prettyPrinter()
        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)] 



class ActionOthersSchedule(Action):

    def name(self) -> Text:
        return "action_others_schedule"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        time = tracker.get_slot("time")
        # print(time)
        handle_time = HandleTime(time, range_=False)
        date = handle_time.get_time_from_duckling()

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email_ = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        print("name before removing 's: ", name)
        if "'s" in name: 
            name = name.replace("'s", "")
        print("name after removing 's: ", name)

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        # employee_db = {"deepak": "deepak.puri@intellificial.com", "monica": "monica.qin@intellificial.com", "vishal": "vishal.pasupathi@intellificial.com", "bharti":"bharti.sinha@intellificial.com"}
        # employee_db = {"deepak": "deepak.puri@intellificial.com", 
        #                 "monica": "monica.qin@intellificial.com", 
        #                 "vishal": "vishal.pasupathi@intellificial.com", 
        #                 "bharti":"bharti.sinha@intellificial.com",
        #                 "tanuj": "tanuj.kapoor@intellificial.com",
        #                 "shilpa": "shilpa.george@intellificial.com",
        #                 "deepika": "deepika.saksena@intellificial.com",
        #                 "gauri":"gauri.khopkar@intellificial.com",
        #                 "sunita": "sunita.verma@intellificial.com"}

        # if name.lower() in employee_db:
        #     email = employee_db[name.lower()]
        # else:
        #     dispatcher.utter_message(text="The employee does not exist.")
        #     return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time=None, to_time=None, range=False, name=name)
            meetings = response.prettyPrinter()
        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

class ActionOthersScheduleAmbiguous(Action):

    def name(self) -> Text:
        return "action_others_schedule_ambiguous"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        # # employee_db = {"deepak": "deepak.puri@intellificial.com", "monica": "monica.qin@intellificial.com", "vishal": "vishal.pasupathi@intellificial.com", "bharti":"bharti.sinha@intellificial.com"}
        # employee_db = {"deepak": "deepak.puri@intellificial.com", 
        #                 "monica": "monica.qin@intellificial.com", 
        #                 "vishal": "vishal.pasupathi@intellificial.com", 
        #                 "bharti":"bharti.sinha@intellificial.com",
        #                 "tanuj": "tanuj.kapoor@intellificial.com",
        #                 "shilpa": "shilpa.george@intellificial.com",
        #                 "deepika": "deepika.saksena@intellificial.com",
        #                 "gauri":"gauri.khopkar@intellificial.com",
        #                 "sunita": "sunita.verma@intellificial.com"}

        # if name.lower() in employee_db:
        #     email = employee_db[name.lower()]
        # else:
        #     dispatcher.utter_message(text="The employee does not exist.")
        #     return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time=None, to_time=None, range=False, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]


class ActionOthersScheduleRange(Action):

    def name(self) -> Text:
        return "action_others_schedule_range"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        time = tracker.get_slot("time")
        print(time)
        handle_time = HandleTime(time, range_=True)
        from_time, to_time, date = handle_time.get_time_from_duckling()

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        # # employee_db = {"deepak": "deepak.puri@intellificial.com", "monica": "monica.qin@intellificial.com", "vishal": "vishal.pasupathi@intellificial.com", "bharti":"bharti.sinha@intellificial.com"}
        # employee_db = {"deepak": "deepak.puri@intellificial.com", 
        #                 "monica": "monica.qin@intellificial.com", 
        #                 "vishal": "vishal.pasupathi@intellificial.com", 
        #                 "bharti":"bharti.sinha@intellificial.com",
        #                 "tanuj": "tanuj.kapoor@intellificial.com",
        #                 "shilpa": "shilpa.george@intellificial.com",
        #                 "deepika": "deepika.saksena@intellificial.com",
        #                 "gauri":"gauri.khopkar@intellificial.com"}

        # if name.lower() in employee_db:
        #     email = employee_db[name.lower()]
        # else:
        #     dispatcher.utter_message(text="The employee does not exist.")
        #     return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

class ActionRangeAmbiguous(Action):

    def name(self) -> Text:
        return "action_range_ambiguous"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        # time = tracker.get_slot("time")
        # print(time)
        # handle_time = HandleTime(time, range_=True)
        # from_time, to_time, date = handle_time.get_time_from_duckling()

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        datetime_str_from = "24AUG2001120000"
        datetime_str_to = "24AUG2001190000"

        datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
        datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

        from_time = datetime_obj_from.time()
        to_time = datetime_obj_to.time()

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

class ActionRangeWeird(Action):

    def name(self) -> Text:
        return "action_range_weird"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        if "afternoon" in tracker.latest_message['text'] or "aftrnoon" in tracker.latest_message['text'] or "noon" in tracker.latest_message['text']:
            datetime_str_from = "24AUG2001120000"
            datetime_str_to = "24AUG2001190000"

            datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
            datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

            from_time = datetime_obj_from.time()
            to_time = datetime_obj_to.time()

        elif "morning" in tracker.latest_message['text'] or "mrng" in tracker.latest_message['text'] :
            datetime_str_from = "24AUG2001000000"
            datetime_str_to = "24AUG2001120000"
            datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
            datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

            from_time = datetime_obj_from.time()
            to_time = datetime_obj_to.time()
        
        elif "evening" in tracker.latest_message['text'] or "evng" in tracker.latest_message['text']:
           datetime_str_from = "24AUG2001190000"
           datetime_str_to = "24AUG2001000000"
           datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
           datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")
           from_time = datetime_obj_from.time()
           to_time = datetime_obj_to.time()

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]



# # class ActionPostlunchRangeWeird(Action):

#     def name(self) -> Text:
#         return "action_postlunch_range_weird"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

#         printt = PrintBasicInfo(tracker)
#         printt.run()

#         slot_value_temp=[]
#         for slot_name in SLOTS_FILLED:
#             temp_tuple = (slot_name, tracker.get_slot(slot_name))
#             slot_value_temp.append(temp_tuple)
#         # print(slot_value_temp)

#         today = datepkg.today()
#         # print("Today's date:", today)
#         date = today.strftime("%Y-%m-%d")
#         date = date.split("-")

#         if "lunch" in tracker.latest_message['text'] or "post lunch" in tracker.latest_message['text']:
#             datetime_str_from = "24AUG2001120000"
#             datetime_str_to = "24AUG2001190000"

#             datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
#             datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

#             from_time = datetime_obj_from.time()
#             to_time = datetime_obj_to.time()

       

#         # get the sender's email id
#         user = ActionCheckUserInfo()
#         username, email = user.run(dispatcher, tracker, domain)

#         name = tracker.get_slot("name")
#         name = name.replace("'s", "")

#         row = [username, 
#                 tracker.latest_message["text"], 
#                 tracker.latest_message["intent"], 
#                 "action_personal_schedule_ambiguous", 
#                 slot_value_temp,
#                 name]

#         STORE.run(row)

#         name_list=[]
#         for employee in EMPLOYEE_DB:
#             # print("first name: ", employee.get_first_name())
#             if name.lower() == employee.get_first_name():
#                 # print("IN")
#                 name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
#                 # email = employee.get_email()
#             # print("name_list: ", name_list)

#         if len(name_list) > 1:
#             # there are two employees with same name
#             # surnames = []
#             textt = "Do you want to know about "
#             for name in name_list:
#                 # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
#                 textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
#             textt = textt[:-5] + "?"
#             dispatcher.utter_message(text=textt)
#             return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
#         elif len(name_list) == 1:
#             # there is only one employee with the name
#             email = name_list[0][0]
#             # print("print email ", email)
#         elif len(name_list) == 0:
#             dispatcher.utter_message(text="The employee does not exist.")
#             return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

#         # get the associated calender
#         my_calendar = GetCalendar(email, date)
#         all_events = my_calendar.get_calendar()
#         if isinstance(all_events, str):
#             meetings = all_events
#         else:
#             response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
#             meetings = response.prettyPrinter()

#         help = "If there is anything else I can help you with, please type in your queries to get started."

#         dispatcher.utter_message(text=meetings)
#         dispatcher.utter_message(text=help)
#         return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]



class ActionReplyContractPartTime(Action):

    def name(self) -> Text:
        return "action_reply_contract_part_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        message = "Part-time employees have ongoing employment and typically work less than 38 hours a week. They usually work regular hours each week and are entitled to the same minimum employment entitlements as full-time staff. However, the part-time entitlements are on a 'pro rata' basis."

        dispatcher.utter_message(text=message)


class ActionReplyContractFullTime(Action):

    def name(self) -> Text:
        return "action_reply_contract_full_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        message = "Full-time employees have ongoing employment and generally work 38 ordinary hours per week or an average of 38 ordinary hours a week. They are entitled to paid leave and are required to be given notice of termination."

        dispatcher.utter_message(text=message)


class ActionReplyContractIndependent(Action):

    def name(self) -> Text:
        return "action_reply_contract_independent"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        message = "Independent contractors are typically self-employed workers who contract their services out to other companies. Contractors negotiate their own fees and working arrangements and they have the freedom to work for multiple employers at once. It's important for an employer to clearly define whether the person they hire is a permanent employee or independent contractor as there may be risks to the business if the contractor turns out to be an employee."

        dispatcher.utter_message(text=message)



class ActionReplyContractfixed(Action):

    def name(self) -> Text:
        return "action_reply_contract_fixed"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        # TODO: WRTITE ROW

        message = "Fixed-term contracts clearly outline the length of the employment period from start to end. Although this type of arrangement is often short-term, fixed-term workers still receive the same entitlements as permanent employees though notice is not required if the employment contract ends at the end of the fixed-term."
        dispatcher.utter_message(text=message)


class ActionCheckConfirmation(Action):

    def name(self) -> Text:
        return "action_check_affirmation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        # list_of_bot_utterances_names =[]
         
        for dicti in tracker.current_state()["events"]:
            if dicti["event"] == "bot":
                # print(dicti)
                try:
                    # list_of_bot_utterances_names.append(dicti["metadata"]["utter_action"])
                    list_of_bot_utterances_names = dicti["metadata"]["utter_action"]
                except Exception as e:
                    continue
        print("list_of_bot_utterances_names", list_of_bot_utterances_names)
        # print(list_of_bot_utterances_names[-1])
        if list_of_bot_utterances_names == 'utter_work_overtime':
            # print(tracker.latest_message["intent"])
            if tracker.latest_message["intent"]["name"] == "affirm":

                text1 = "The employee will be eligible for overtime pay if the client agrees to pay overtime rates to Intellificial. If yes, overtime is paid:\n"

                text2 = " 1. Time and a half (150%) of ordinary rate in the first 2-3 hours; and\n"
                text3 = " 2. Double time (200%) of ordinary rate after the first 2-3 hours.\n\n"
                text4 = " Differential pay mentioned above will be paid to eligible employee conditioning the client compensates the differential value to the Intellificial.\n\n"
                text5 = " Eligible employee can choose TOIL/Compensatory off in place of overtime pay. This decision needs to be communicated to HR and Manager on e-mail by the employee. "
                
                message = text1 + text2 + text3 + text4 + text5
                dispatcher.utter_message(text=message)
            
            if tracker.latest_message["intent"]["name"] == "deny":
                message = "Thanks for your response. Let me know if you have any other question, I'm here to help you😊."
                dispatcher.utter_message(text=message) 


        #--------------TOIL Confirmation Task --------------------------------------------------------#
        
        if list_of_bot_utterances_names == 'utter_time_Off_in_lieu':
            # print(tracker.latest_message["intent"])
            if tracker.latest_message["intent"]["name"] == "affirm":

                # text1 = "<b>Mail draft for pre-approval:</b> \n"
                # text2 = "To: Client manager\\n"
                # text3 = "CC: Intellificial manager, HR\ \n "
                # text4 = "Subject line: Approval for expected over-time on <Date(s)\ \n "
                # text5 = "Hi Client Manager,\ \n "
                # text6 = "As agreed, can you please confirm that I’m required to do overtime work on <Date (s)> for <No. of hours> and or <start time> to <end time> to meet the current project needs. Your approval is requested to keep Intellificial team posted on this arrangement.\ \n"
                # text7 = "Thank you!\ \n "
                # text8 = "Kind Regards\ \n "
                # text9 = "Employee Name"
                # message = text1 + text2 + text3 + text4 + text5 + text6 + text7 + text8 + text9
                # text1 = "<b>Mail draft for pre-approval:</b> 
                # text2 =  "To: <Client manager>   \ \n "
                # text3 =  "CC: <Intellificial manager's name>, <HR's name>   \ \n "
                # text4 =  "Subject line: Approval for expected over-time on <Date(s)   \ \n "
                # text5 =  "Hi <Client Manager's name>,    \ \n "
                # text6 =  "As agreed, can you please confirm that I’m required to do overtime work on <Date (s)> for <b><No. of hour(s)></b> and or <start time()> to <end time()> to meet the current project needs. Your approval is requested to keep Intellificial team posted on this arrangement.  \ \n "
                # text7 =  "Thank you! \ \n "
                # text8 =  "Kind Regards   \ \n"
                # text9 =  "<Employee's Name>"
                # message = text1 + text2 + text3 + text4 + text5 + text6 + text7 + text8 + text9
                dispatcher.utter_message(response = "utter_mail_draft")
                # dispatcher.utter_message(text= message)
             
            if tracker.latest_message["intent"]["name"] == "deny":
                message = "Thanks for your response. Let me know if you have any other question, I'm here to help you😊."
                dispatcher.utter_message(text=message)    


        #--------------------------------Goal Setting-------------------------------------------
        if list_of_bot_utterances_names == 'utter_ask_goal_setting':
            # print(tracker.latest_message["intent"])
            if tracker.latest_message["intent"]["name"] == "affirm":
                dispatcher.utter_message(response = "utter_goal_setting_steps")
            if tracker.latest_message["intent"]["name"] == "deny":
                message = "Thanks for your response. Let me know if you have any other question, I'm here to help you😊."
                dispatcher.utter_message(text=message)     

# class ActionCheckConfirmationLieuPolicy(Action):

#     def name(self) -> Text:
#         return "action_check_affirmation_lieu_policy"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

#         printt = PrintBasicInfo(tracker)
#         printt.run()

#         list_of_bot_utterances_names =[]
#         for dicti in tracker.current_state()["events"]:
#             if dicti["event"] == "bot":
#                 # print(dicti)
#                 try:
#                     list_of_bot_utterances_names.append(dicti["metadata"]["utter_action"])
#                 except Exception as e:
#                     continue
        
#         print(list_of_bot_utterances_names[-1])
#         #--------------TOIL Confirmation Task --------------------------------------------------------#
#          if list_of_bot_utterances_names[-1] == 'utter_time_Off_in_lieu':
#             # print(tracker.latest_message["intent"])
#             if tracker.latest_message["intent"]["name"] == "affirm":

#                 text1 = " Mail draft for pre-approval:\n"
#                 text2 = " To: <Client manager>\n"
#                 text3 = " CC: <Intellificial manager>, <HR>\n\n"
#                 text4 = " Subject line: Approval for expected over-time on <Date(s)\n\n"
#                 text5 = " Hi <Client Manager>,\n\n "
#                 text6 = " As agreed, can you please confirm that I’m required to do overtime work on <Date (s)> for <No. of hours> and or <start time> to <end time> to meet the current project needs. Your approval is requested to keep Intellificial team posted on this arrangement.\n\n"
#                 text7 = "Thank you!\n"
#                 text8 = "Kind Regards\n"
#                 text9 = "<Employee Name>"
#                 message = text1 + text2 + text3 + text4 + text5 + text6 + text7 + text8 + text9
#                 dispatcher.utter_message(text=message)
            
#             if tracker.latest_message["intent"]["name"] == "deny":
#                 message = "Thanks for your response. Let me know if you have any other question, I'm here to help you😊."
#                 dispatcher.utter_message(text=message) 



class ActionPersonalPostlunchSchedule(Action):

    def name(self) -> Text:
        return "action_personal_postlunch_schedule"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)
        # today = datepkg.today()
        # # print("Today's date:", today)
        # date = today.strftime("%Y-%m-%d")
        # date = date.split("-")

        time = tracker.get_slot("time")
        if type(time) is dict:
            T1 = next(iter((time.items())) )
            time = T1[1]

        print("peronal_ postlunch time : ",time)
        handle_time = HandleTime(time, range_= False)
        print("handle_time: ",handle_time)        
        date = handle_time.get_time_from_duckling()
        print("date_and_time: ",date)

        print("date: ",date)

        datetime_str_from = "24AUG2001120000"
        datetime_str_to = "24AUG2001190000"

        datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
        datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

        from_time = datetime_obj_from.time()
        to_time = datetime_obj_to.time()

        print("from_time: ",from_time)
        print("to_time: ",to_time)

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                "self"]

        STORE.run(row)

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True)
            meetings = response.prettyPrinter()
        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)] 


class ActionPersonalPostlunchScheduleAmbiguous(Action):

    def name(self) -> Text:
        return "action_personal_postlunch_schedule_ambiguous"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)
        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        time = tracker.get_slot("time")
        # print(time)
        handle_time = HandleTime(time, range_=True)
        # from_time, to_time, date = handle_time.get_time_from_duckling()
        datetime_str_from = "24AUG2001120000"
        datetime_str_to = "24AUG2001190000"

        datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
        datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

        from_time = datetime_obj_from.time()
        to_time = datetime_obj_to.time()

        print("from_time: ",from_time)
        print("to_time: ",to_time)

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                "self"]

        STORE.run(row)

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True)
            meetings = response.prettyPrinter()
        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)] 



class ActionOthersPostlunchScheduleAmbiguous(Action):

    def name(self) -> Text:
        return "action_others_postlunch_schedule_ambiguous"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        today = datepkg.today()
        # print("Today's date:", today)
        date = today.strftime("%Y-%m-%d")
        date = date.split("-")

        time = tracker.get_slot("time")
        print(time)
        handle_time = HandleTime(time, range_=True)
        # from_time, to_time, date = handle_time.get_time_from_duckling()

        datetime_str_from = "24AUG2001120000"
        datetime_str_to = "24AUG2001190000"

        datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
        datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

        from_time = datetime_obj_from.time()
        to_time = datetime_obj_to.time()

        print("from_time: ",from_time)
        print("to_time: ",to_time)

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        # # employee_db = {"deepak": "deepak.puri@intellificial.com", "monica": "monica.qin@intellificial.com", "vishal": "vishal.pasupathi@intellificial.com", "bharti":"bharti.sinha@intellificial.com"}
        # employee_db = {"deepak": "deepak.puri@intellificial.com", 
        #                 "monica": "monica.qin@intellificial.com", 
        #                 "vishal": "vishal.pasupathi@intellificial.com", 
        #                 "bharti":"bharti.sinha@intellificial.com",
        #                 "tanuj": "tanuj.kapoor@intellificial.com",
        #                 "shilpa": "shilpa.george@intellificial.com",
        #                 "deepika": "deepika.saksena@intellificial.com",
        #                 "gauri":"gauri.khopkar@intellificial.com"}

        # if name.lower() in employee_db:
        #     email = employee_db[name.lower()]
        # else:
        #     dispatcher.utter_message(text="The employee does not exist.")
        #     return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]


class ActionOthersPostlunchSchedule(Action):

    def name(self) -> Text:
        return "action_others_postlunch_schedule"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 

        printt = PrintBasicInfo(tracker)
        printt.run()

        slot_value_temp=[]
        for slot_name in SLOTS_FILLED:
            temp_tuple = (slot_name, tracker.get_slot(slot_name))
            slot_value_temp.append(temp_tuple)
        # print(slot_value_temp)

        # today = datepkg.today()
        # # print("Today's date:", today)
        # date = today.strftime("%Y-%m-%d")
        # date = date.split("-")

        time = tracker.get_slot("time")
        print(time)
        handle_time = HandleTime(time, range_=True)
        from_time, to_time, date = handle_time.get_time_from_duckling()

        datetime_str_from = "24AUG2001120000"
        datetime_str_to = "24AUG2001190000"

        datetime_obj_from = dt.strptime(datetime_str_from,"%d%b%Y%H%M%S")
        datetime_obj_to = dt.strptime(datetime_str_to,"%d%b%Y%H%M%S")

        from_time = datetime_obj_from.time()
        to_time = datetime_obj_to.time()

        print("from_time: ",from_time)
        print("to_time: ",to_time)

        # get the sender's email id
        user = ActionCheckUserInfo()
        username, email = user.run(dispatcher, tracker, domain)

        name = tracker.get_slot("name")
        name = name.replace("'s", "")

        row = [username, 
                tracker.latest_message["text"], 
                tracker.latest_message["intent"], 
                "action_personal_schedule_ambiguous", 
                slot_value_temp,
                name]

        STORE.run(row)

        # # employee_db = {"deepak": "deepak.puri@intellificial.com", "monica": "monica.qin@intellificial.com", "vishal": "vishal.pasupathi@intellificial.com", "bharti":"bharti.sinha@intellificial.com"}
        # employee_db = {"deepak": "deepak.puri@intellificial.com", 
        #                 "monica": "monica.qin@intellificial.com", 
        #                 "vishal": "vishal.pasupathi@intellificial.com", 
        #                 "bharti":"bharti.sinha@intellificial.com",
        #                 "tanuj": "tanuj.kapoor@intellificial.com",
        #                 "shilpa": "shilpa.george@intellificial.com",
        #                 "deepika": "deepika.saksena@intellificial.com",
        #                 "gauri":"gauri.khopkar@intellificial.com"}

        # if name.lower() in employee_db:
        #     email = employee_db[name.lower()]
        # else:
        #     dispatcher.utter_message(text="The employee does not exist.")
        #     return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        name_list=[]
        for employee in EMPLOYEE_DB:
            # print("first name: ", employee.get_first_name())
            if name.lower() == employee.get_first_name():
                # print("IN")
                name_list.append((employee.get_email(), EMPLOYEE_DB.index(employee)))
                # email = employee.get_email()
            # print("name_list: ", name_list)

        if len(name_list) > 1:
            # there are two employees with same name
            # surnames = []
            textt = "Do you want to know about "
            for name in name_list:
                # surnames.append(EMPLOYEE_DB[name[1]].get_surname())
                textt = textt + EMPLOYEE_DB[name[1]].get_first_name() + " " + EMPLOYEE_DB[name[1]].get_surname() + ", or "
            textt = textt[:-5] + "?"
            dispatcher.utter_message(text=textt)
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]
        elif len(name_list) == 1:
            # there is only one employee with the name
            email = name_list[0][0]
            # print("print email ", email)
        elif len(name_list) == 0:
            dispatcher.utter_message(text="The employee does not exist.")
            return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

        # get the associated calender
        my_calendar = GetCalendar(email, date)
        all_events = my_calendar.get_calendar()
        if isinstance(all_events, str):
            meetings = all_events
        else:
            response = Response(all_events, date, tracker, my_calendar, from_time, to_time, range=True, name=name)
            meetings = response.prettyPrinter()

        help = "If there is anything else I can help you with, please type in your queries to get started."

        dispatcher.utter_message(text=meetings)
        dispatcher.utter_message(text=help)
        return [SlotSet("time", None), SlotSet("name", None), SlotSet("employee", None)]

