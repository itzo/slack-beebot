#!/usr/bin/env python
import os
import time
from slackclient import SlackClient

channel = '#general'
users = {}

# parse slack events for reactions / commands
def parse_event(event):
    print str(event) + '\n'

# get the list of users and their names for later use
def get_users():
    data = sc.api_call('users.list', channel='#general')
    for user in data['members']:
        print 'id: %s, name: %s' % (user['id'], user['name'])
        users[user['id']] = user['name']

# main
if __name__ == '__main__':
    token = os.environ.get('SLACK_BOT_TOKEN')
    sc = SlackClient(token)
    if sc.rtm_connect():
        print('Bot connected and running!')
        get_users()
        while True:
            parse_event(sc.rtm_read())
            time.sleep(1)
    else:
        print 'Connection failed. Check token.'
