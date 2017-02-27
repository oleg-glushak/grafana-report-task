#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import print_function
import httplib2
import os
import sys
import platform

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import datetime
from datetime import date, time
import smtplib
from email.mime.text import MIMEText
from jira import JIRA
# from jira import JIRAError

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = '.client_secret.json'
STORED_SECRETS = '.secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

ADMIN_CALENDAR_ID = '<id>'

MSG_CONTENT_GENERAL = "Failed to create grafana_report weekly tasks in Jira. Make it manually."
MSG_CONTENT_NO_EVENTS_FOUND = "No events found in Google Calendar"
MSG_CONTENT_CANT_GET_CALENDAR_EVENTS = "Can't get Google calendar events"
MSG_CONTENT_CANT_CREATE_JIRA_TASK = "Can't create Jira task"
MSG_SUBJECT = 'Failed to create Jira grafana_report weekly task'
MSG_FROM = "Jira <foo@mocomedia.ru>"
MSG_TO = "o.glushak@mocomedia.ru"
SMTP_SERVER = 'foo.bar'

JIRA_HOST = 'http://jira.foo.bar'
JIRA_USER = '<jira-user>'
JIRA_PASSWORD = '<jira-pass>'
JIRA_ISSUE_STATUS = 'На исполнение'
JIRA_ISSUE_SUMMARY = 'Еженедельный Grafana отчет (' + datetime.datetime.today().strftime("%Y-%m-%d") + ")"
JIRA_ISSUE_DESCRIPTION = 'Просмотреть графики Grafana в месячном разрезе для выявления аномалий и просмотреть ' \
                         'Oracle-предсказания'
JIRA_PROJECT = 'AD'


def create_jira_task(host, user, password, assignee):
    jira = JIRA(basic_auth=(user, password), server=host)
    issue = jira.create_issue(project=JIRA_PROJECT, summary=JIRA_ISSUE_SUMMARY,
                                   description=JIRA_ISSUE_DESCRIPTION, issuetype={'name': 'Task'})
    username = jira.search_users(assignee, maxResults=1)[0].name
    issue.update(assignee={'name': username})
    transition_id = jira.find_transitionid_by_name(issue.id, JIRA_ISSUE_STATUS)
    jira.transition_issue(issue.id, transition_id)


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    # home_dir = os.path.expanduser('~')
    # credential_dir = os.path.join(home_dir, '.credentials')
    # if not os.path.exists(credential_dir):
    #     os.makedirs(credential_dir)

    credential_path = os.path.join(sys.path[0], STORED_SECRETS)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    today = datetime.datetime.combine(date.today(), time())
    sunday = (today - datetime.timedelta(today.weekday() + 1)).isoformat() + 'Z'

    try:
        eventsResult = service.events().list(
            calendarId=ADMIN_CALENDAR_ID, timeMin=sunday, maxResults=1, singleEvents=True,
            orderBy='startTime').execute()

        events = eventsResult.get('items', [])
    except Exception as e:
        raise MocoCantGetCalendarEvents(str(e))

    if not events:
        raise MocoEventsNotFound(MSG_CONTENT_NO_EVENTS_FOUND)
    for event in events:
        # start = event['start'].get('dateTime', event['start'].get('date'))
        assignee = event['summary']
        try:
            create_jira_task(JIRA_HOST, JIRA_USER, JIRA_PASSWORD, assignee)
        except Exception as e:
            pass
            raise MocoCantCreateJiraTask(str(e))
        # print(start, event['summary'])
        break


class MocoWeeklyTaskError(Exception):
    def __init__(self, error=MSG_CONTENT_GENERAL):
        self.__send_mail__(MSG_FROM, MSG_TO, error, MSG_SUBJECT, SMTP_SERVER)

    def __send_mail__(self, sender, to, msg, subject, smtp_server):
        content = MIMEText("Host: %s\nScript: %s\n%s" % (platform.node(), sys.argv[0], msg))
        content['Subject'] = subject
        content['From'] = sender
        content['To'] = to
        s = smtplib.SMTP(smtp_server)
        s.sendmail(sender, to, content.as_string())
        s.quit()


class MocoEventsNotFound(MocoWeeklyTaskError):
    pass


class MocoCantGetCalendarEvents(MocoWeeklyTaskError):
    pass


class MocoCantCreateJiraTask(MocoWeeklyTaskError):
    pass

if __name__ == '__main__':
    main()
