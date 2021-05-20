slack-beebot
====================================================

Beebot is a python slack bot that counts and reports on users reactions.
It uses the Slack RTM API and the slackclient library.

|build-status|

QuickStart
==========

1. Clone the git repository:
```
git clone git@github.com:itzo/slack-beebot.git
```
2. Install Required Library:
```
pip install slackclient
```
3. Add necessary Bot integration in Slack
   From slack click the "+" next to Apps, then search for Bot and add the one
   named "Bots". This will add a classic bot that uses the RTM API (legacy).
   Once added, get its bot token (starts with "xoxb-....").

4. Set environmental variables:
```
export SLACK_BOT_TOKEN="xoxb-111111111111-XXXXXXXXXXXXXXXXXXXXXXXX"
```
5. Use Beebot:
```
cd slack-beebot && python beebot.py
```
Alternatively run it using docker
```
docker build -t beebot .
docker run -d -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN beebot
```

Requirements
============

slack-beebot requires the following modules:

* Python 2.7+
* slackclient

.. |build-status| image:: https://travis-ci.org/itzo/slack-beebot.svg?branch=master
   :target: https://travis-ci.org/itzo/slack-beebot
   :alt: Build status
