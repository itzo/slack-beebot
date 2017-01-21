#!/usr/bin/env python

import datetime
import websocket
import os
import time
from slackclient import SlackClient
import sqlite3 as db
import subprocess
import sys
import re

# TODO: add logging mechanism
# TODO: add daemonize and if connection goes down - reconnect automatically
# TODO: add args parser (debug, daemonize)
# TODO: exclude bot from stats

token = os.environ.get('SLACK_BOT_TOKEN')
users, channels, ims = {}, {}, {}
rev_parse_head = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
time_started = str(datetime.datetime.now())

# add timestamp to all print statements
old_out = sys.stdout
class timestamped:
    nl = True

    def write(self, x):
        # overload write()
        if x == '\n':
            old_out.write(x)
            self.nl = True
        elif self.nl:
            old_out.write('[ %s ] %s' % (str(int(time.time())), x))
            self.nl = False
        else:
            old_out.write(x)
sys.stdout = timestamped()


# crate db table if none exists
def create_db():
    try:
        con = db.connect('reactions.db')
        cur = con.cursor()
        cur.execute('DROP TABLE IF EXISTS reactions')
        cur.executescript("""
            CREATE TABLE reactions(
                from_user TEXT,
                to_user TEXT,
                reaction TEXT,
                counter INTEGER
            );""")
        con.commit()
    except db.Error, e:
        if con:
            con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()


# insert reaction into db table
def db_insert(from_user, to_user, reaction, counter):
    if os.path.isfile('reactions.db'):
        con = db.connect('reactions.db')
        cur = con.cursor()
        cur.execute('INSERT INTO reactions VALUES(?,?,?,?)', \
            (from_user, to_user, reaction, counter));
        con.commit()
    else:
        print "Can't find the database.\n"
        sys.exit(2)


# parse slack events for reactions / commands
def parse_event(event):
    #print str(event) + '\n'
    if event and len(event) > 0:

        # process reactions
        data = event[0]
        if all(x in data for x in ['user', 'item_user', 'reaction']):
            reaction = data['reaction']
            from_user = data['user']
            to_user = data['item_user']
            if data['type'] == 'reaction_added' and from_user != to_user:
                print "%s reacted with '%s' to %s" % (users[from_user], reaction, users[to_user])
                counter = '1'
                db_insert(from_user, to_user, reaction, counter)
            elif data['type'] == 'reaction_removed' and from_user != to_user:
                print "%s withdrew their reaction of '%s' from %s" % (users[from_user], reaction, users[to_user])
                counter = '-1'
                db_insert(from_user, to_user, reaction, counter)
            return reaction, from_user, to_user

        # answer commands
        if 'text' in data:
            channel_id = data['channel']
            if data['text'].lower().startswith('showme'):
                if len(data['text'].split()) > 2:
                    mode = data['text'].lower().split()[1]
                    reaction = data['text'].lower().split()[2]
                    if re.match(r'^[A-Za-z0-9_+]+$', reaction):
                        from_user = data['user']
                        if channel_id in channels:
                            print "%s requested to see %s %s in #%s" % (users[from_user], mode, reaction, channels[channel_id])
                        else:
                            print "%s requested to see %s %s via IM" % (users[from_user], mode, reaction)
                        # FIXME: add an arg to switch between DM or in other channels
                        if (True == True):
                            channel_id = data['user']
                        print_top(reaction, channel_id, mode)
                    else:
                        bot_usage(channel_id)
                else:
                    bot_usage(channel_id)
            elif len(data['text'].split()) > 1 and data['text'].lower().startswith('beebot'):
                # FIXME: add an arg to switch between DM or in other channels
                if (True == True):
                    channel_id = data['user']
                if data['text'].lower().split()[1] == 'version':
                   bot_version(channel_id)
    return None, None, None


# send a message with the correct way to use the bot
def bot_usage(channel_id):
    text = '''```
usage:
    {:{w}} {:{w}} 
    {:{w}} {:{w}} 
```'''.format(
        'showme', '[top|all] <reaction>',
        'beebot', '[version]',
        w=7,
    )
    sc.api_call("chat.postMessage", channel=channel_id, text=text, as_user=True)

# report code version (git HEAD rev), start time, etc
def bot_version(channel_id):
    text = '''```
{:{w}} {:{w}} 
{:{w}} {:{w}} 
```'''.format(
    'started:', time_started,
    'head:', rev_parse_head,
    w=14,
    )
    sc.api_call("chat.postMessage", channel=channel_id, text=text, as_user=True)


# print top recipients of a reaction
def print_top(reaction, channel_id, mode):
    if os.path.isfile('reactions.db'):
        con = db.connect('reactions.db')
        with con:
            cur = con.cursor()
            sql = "SELECT to_user, sum(counter) as count from reactions where reaction=? group by to_user order by count desc"
            if mode == 'top':
                sql += " limit 5"
            elif mode == 'all':
                donothing = 'no op'
            else:
                bot_usage(channel_id)
                return
            cur.execute(sql, [reaction])
            con.commit()
            rows = cur.fetchall()
            print "Showing %s %s" % (mode, reaction)
            response = "```"
            if len(rows) > 0:
                for row in rows:
                    print "%-14s %+14d" % (users[row[0]], row[1])
                    response += "{:14} {:14d}\n".format(users[row[0]],row[1])
            else:
                response += "no '"+reaction+"' reactions found"
                print "none found"
            response += "```"
            sc.api_call("chat.postMessage", channel=channel_id, text=response, as_user=True)
    else:
        print "Can't find the database.\n"
        sys.exit(2)


# get slack team info such as users, channels, and im's for later use
def get_info():
    # get user data
    user_data = sc.api_call('users.list')
    for user in user_data['members']:
        print 'id: %s, name: %s' % (user['id'], user['name'])
        users[user['id']] = user['name']
    # get channel data
    chan_data = sc.api_call('channels.list')
    for chan in chan_data['channels']:
        print 'chan: %s, name: %s' % (chan['id'], chan['name'])
        channels[chan['id']] = chan['name']
    # get im data
    im_data = sc.api_call('im.list')
    for im in im_data['ims']:
        print 'im: %s, user: %s' % (im['id'], users[im['user']])
        ims[im['id']] = users[im['user']]


# main
if __name__ == '__main__':
    # initialize db if it doesn't exist
    if os.path.exists('./reactions.db') == False:
        create_db()
    # connect to slack
    sc = SlackClient(token)
    try:
        if sc.rtm_connect():
            print('Bot connected and running!')
            get_info()
            while True:
                reaction, from_user, to_user = parse_event(sc.rtm_read())
                time.sleep(1)
        else:
            print 'Connection failed. Check token.'
    except websocket._exceptions.WebSocketConnectionClosedException:
        print 'Connection closed. Did someone disable the bot integration?'

