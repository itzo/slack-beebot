slack-beebot
====================================================

Beebot is a python slack bot that counts and reports on users reactions.
It uses the Slack RTM API and the slackclient library.

|build-status|

QuickStart
==========

1. Clone the git repository:

    git clone git@github.com:itzo/slack-beebot.git

2. Install Required Library:

    pip install slackclient

3. Add necessary Bot integration in Slack

4. Set environmental variables:

	export SLACK_BOT_TOKEN="xoxb-111111111111-XXXXXXXXXXXXXXXXXXXXXXXX"

5. Use Beebot:

	cd slack-beebot
	python beebot.py

Requirements
============

slack-beebot requires the following modules:

* Python 2.7+
* slackclient

.. |build-status| image:: https://travis-ci.org/itzo/slack-beebot.svg?branch=master
   :target: https://travis-ci.org/itzo/slack-beebot
   :alt: Build status
