#!/usr/bin/env python

import argparse
import datetime
import os
import re
import time
from slackclient import SlackClient
import sqlite3 as db
import subprocess
import sys
import websocket, socket, errno

# TODO: add logging mechanism
# TODO: exclude all bots (slackbot, beebot, etc..) from stats

token = os.environ.get('SLACK_BOT_TOKEN')
users, channels, ims, emojis = {}, {}, {}, {}
rev_parse_head = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
time_started = str(datetime.datetime.now())
con_retry = 0


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


# get arguments and usage
def get_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-m', '--mode', default='dm', choices=['quiet', 'dm', 'channel'],
        help="""where MODE can be one of [quiet|dm|channel].
- quiet            don't reply to 'showme' requests.
- dm (default)     send replies via direct message just to the requestor.
- channel          reply where the request was received (channel/dm).""")
    parser.add_argument('-d', '--debug', action='store_true',
        help='print debug messages.')
    return parser


# parse and validate arguments
def parse_args():
    parser = get_parser()
    args = parser.parse_args()
    return args


# create db table if none exists
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
    if args.debug is True:
        print str(event) + '\n'
    if event and len(event) > 0:

        # process reactions
        data = event[0]
        if all(x in data for x in ['user', 'item_user', 'reaction']):
            reaction = data['reaction'].split(':')[0] # strip skin-tones
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
            if args.mode == 'quiet':
                return None, None, None
            elif args.mode == 'dm':
                if 'user' in data:
                    channel_id = data['user']
            mode = None
            if data['text'].lower().startswith('showme'):
                if len(data['text'].split()) > 1:
                    mode = data['text'].lower().split()[1]
                    if mode == 'version':
                        print "%s requested to see bot version" % (users[data['user']])
                        bot_version(channel_id)
                        return None, None, None
                if len(data['text'].split()) > 2:
                    reaction = data['text'].lower().split()[2]
                    if re.match(r'^[A-Za-z0-9_+-]+$', reaction):
                        from_user = data['user']
                        if channel_id in channels:
                            print "%s requested to see %s %s in #%s" % (users[from_user], mode, reaction, channels[channel_id])
                        else:
                            print "%s requested to see %s %s via IM" % (users[from_user], mode, reaction)
                        if reaction in emojis:
                            reaction = emojis[reaction]
                        print_top(reaction, channel_id, mode)
                    else:
                        bot_usage(channel_id)
                else:
                    bot_usage(channel_id)
    return None, None, None


# send a message with the correct way to use the bot
def bot_usage(channel_id):
    text = '''```
usage:
    {:{w}} {:{w}}
    {:{w}} {:{w}}
```'''.format(
        'showme', '[top|all|clicked] <reaction>',
        'showme', '[version]',
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
                pass
            elif mode == 'clicked':
                sql = "SELECT from_user, sum(counter) as count from reactions where reaction=? group by from_user order by count desc"
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
    # get emoji data
    emoji_data = sc.api_call('emoji.list')
    for entry in emoji_data['emoji']:
        if 'alias:' in emoji_data['emoji'][entry]:
            print 'alias: ' + entry + ' ==> '+ emoji_data['emoji'][entry].split(':')[1]
            emojis[entry] = emoji_data['emoji'][entry].split(':')[1]


# open connection to slack
def sl_connect(retry):
    try:
        if sc.rtm_connect():
            print('INFO: Bot connected and running in [ ' + args.mode + ' ] mode!')
            global con_retry
            con_retry = 0
            get_info()
            while True:
                try:
                    reaction, from_user, to_user = parse_event(sc.rtm_read())
                    time.sleep(1)
                except socket.error, e:
                    if isinstance(e.args, tuple):
                        print "ERROR: errno is %d" % e[0]
                        if e[0] == errno.EPIPE:
                            # remote peer disconnected
                            print "ERROR: Detected remote disconnect"
                            sl_con_retry()
                        else:
                            # some different error
                            print "ERROR: socket error: ", e
                            sl_con_retry()
                    else:
                        print "ERROR: socket error: ", e
                        sl_con_retry()
                        break
                except IOError, e:
                    print "ERROR: IOError: ", e
                    sl_con_retry()
                    break
        else:
            print 'ERROR: Connection failed. Token or network issue.'
            sl_con_retry()
    except websocket._exceptions.WebSocketConnectionClosedException:
        print 'ERROR: Connection closed. Did someone disable the bot integration?'
        sl_con_retry()


def sl_con_retry():
    global con_retry
    con_retry += 1
    print "INFO: Connection retry #%d sleeping for %d seconds..." % (con_retry, con_retry*2)
    time.sleep(con_retry*2)
    sl_connect(con_retry)


# main
if __name__ == '__main__':
    args = parse_args()
    # initialize db if it doesn't exist
    if os.path.exists('./reactions.db') == False:
        create_db()
    # connect to slack
    sc = SlackClient(token)
    sl_connect(con_retry)
