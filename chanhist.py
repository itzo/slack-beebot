#!/usr/bin/env python

import os
import time
from slackclient import SlackClient
import requests
from pprint import pprint

# description: collect all channel history reactions since jan 1 2017 - ts 1483228800

token = os.environ.get('SLACK_BOT_TOKEN')
slack = os.environ.get('SLACK_NAME')
channel_id = os.environ.get('SLACK_CHANNEL_ID')
channel = '#general'
count = 50
users = {}
api = 'https://'+slack+'.slack.com/api/channels.history?token='+token+'&channel='+channel_id+'&count='+str(count)

# If the response includes has_more then the client can make another call, 
# using the ts value of the final messages as the latest param to get the next page of messages.

r = requests.get(api)
data = r.json()
print r.status_code

print api

#pprint(data)

for event in data['messages']:
    if 'reactions' in event and 'user' in event:
        to_user = event['user']
        for entry in event['reactions']:
            for user in entry['users']:
                print "from_user: " + str(user) + " to_user: "  + str(to_user) + " reaction: " + str(entry['name'])


while data['has_more'] == True and int(data['messages'][count-1]['ts'].split('.')[0]) > 1483228800 :
    print "====================================================================="
    print data['has_more']
    print data['messages'][count-1]['ts']
    api = 'https://'+slack+'.slack.com/api/channels.history?token='+token+'&channel='+channel_id+'&count='+str(count)+'&latest='+data["messages"][count-1]["ts"]
    r = requests.get(api)
    data = r.json()
    print r.status_code
    print api
    #pprint(data)
    #pprint(data['messages'][count-1]['ts'])
    for event in data['messages']:
        if 'reactions' in event and 'user' in event:
            to_user = event['user']
            for entry in event['reactions']:
                for user in entry['users']:
                    print "from_user: " + str(user) + " to_user: "  + str(to_user) + " reaction: " + str(entry['name'])
    print "\n\n"




#def parse_event(event):
#    print str(event)

# get the list of users and their names for later use
def get_users():
    sc = SlackClient(token)
    if sc.rtm_connect():
        print('Bot connected and running!')
#        while True:
#            parse_event(sc.rtm_read())
#            time.sleep(1)
    data = sc.api_call('users.list', channel=channel)
    for user in data['members']:
        print 'id: %s, name: %s' % (user['id'], user['name'])
        users[user['id']] = user['name']

get_users()
