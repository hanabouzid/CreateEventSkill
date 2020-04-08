from __future__ import print_function
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime
from datetime import datetime, timedelta
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import httplib2
from googleapiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools

SCOPES = ['https://www.googleapis.com/auth/calendar']
FLOW = OAuth2WebServerFlow(
    client_id='1019838388650-nt1mfumr3cltemeq7js8mjitn7a2kuu7.apps.googleusercontent.com',
    client_secret='rx7eaJ-13TiHqOWIiF-Bxu4L',
    scope='https://www.googleapis.com/auth/contacts.readonly',
    user_agent='Smart assistant box')

class CreateEvent(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(CreateEvent, self).__init__(name="CreateEvent")

    @intent_handler(IntentBuilder("").require("create_event"))
    def createEventt(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)       #dans mycroft on met '/opt/mycroft/skills/createeventskill.hanabouzid/credentials.json'
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

        storage = Storage('info.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid == True:
            credentials = tools.run_flow(FLOW, storage)
        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)
        # Build a service object for interacting with the API. To get an API key for
        # your application, visit the Google API Console
        # and look at your application's credentials page.
        people_service = build(serviceName='people', version='v1', http=http)
        # To get a list of people in the user's contacts,
        results = people_service.people().connections().list(resourceName='people/me', pageSize=100,
                                                             personFields='names,emailAddresses',
                                                             fields='connections,totalItems,nextSyncToken').execute()
        connections = results.get('connections', [])
        #need to verify this
        #self.speak(connections)
        #get informations about the event
        name = self.get_response("what is the name of the event")
        description = self.get_response("can you describe more the event")
        strtdate = self.get_response("when the event starts")
        startdt = extract_datetime(strtdate)
        enddate = self.get_response("when the event ends")
        enddt = extract_datetime(enddate)
        #adding attendees
        # getting contacts emails and names in two lists nameliste and adsmails
        nameListe = []
        adsmails = []
        #attendee est la liste des invités qui sont disponibles
        attendee=[]
        exist = False
        for person in connections:
            emails = person.get('emailAddresses', [])
            names = person.get('names', [])
            adsmails.append(emails[0].get('value'))
            nameListe.append(names[0].get('displayName'))
        #verify if the attendee in the connection liste and if he is free
        confirm= self.get_response("Do you want to invite someone? yes or no?")
        if confirm =='yes':
            n_attendee = self.get_response(" how many persons would you like to invite")
            n = int(n_attendee )
            print(n)
            j = 0
            while j < n:
                x = self.get_response("who do you want to invite")
                for l in range(0,len(nameListe)):
                    if x == nameListe[l]:
                        self.speak_dialog("exist")
                        exist = True
                        mail = adsmails[l]
                        attendee.append(mail)
                        # on va verifier la disponibilité de chaque invité
                        body = {
                            "timeMin":startdt,
                            "timeMax":enddt ,
                            "timeZone": 'US/Central',
                            "items": [{"id":mail}]
                        }
                        eventsResult = service.freebusy().query(body=body).execute()
                        cal_dict = eventsResult[u'calendars']
                        print(cal_dict)
                        for cal_name in cal_dict:
                            print(cal_name, ':', cal_dict[cal_name])
                            statut = cal_dict[cal_name]
                            for i in statut:
                                if (i == 'busy' and statut[i] == []):
                                    self.speak_dialog("free")
                                    #ajouter l'email de x ala liste des attendee
                                elif (i == 'busy' and statut[i] != []):
                                    self.speak_dialog("busy")
                    else:
                        exist = False
                if exist == False:
                    self.speak_dialog("notexist")
                j += 1

        attendeess = []
        for i in range(len(attendee)):
            email = {'email': attendee[i]}
            attendeess.append(email)
        print(attendeess)
        #creation d'un evenement
        event = {
            'summary': name,
            'location': '800 Howard St., San Francisco, CA 94103',
            'description': description,
            'start': {
                'dateTime': startdt,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': enddt,
                'timeZone': 'America/Los_Angeles',
            },
            'recurrence': [
                'RRULE:FREQ=DAILY;COUNT=2'
            ],
            'attendees': attendeess,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        self.speak_dialog("eventCreated")
def create_skill():
    return CreateEvent()
