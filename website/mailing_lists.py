# -*- coding: utf-8 -*-

import requests
import json

from framework import sentry
from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.auth.signals import user_confirmed

from website import settings

from website.settings.local import MAILGUN_API_KEY, MAILGUN_UNSUB_URL

def address(node_id):
    return node_id + '@sandbox366bcd27e2ea4dc1b81db4df458924d3.mailgun.org'

def get_list(node_id):
    info = requests.get(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY),
    )
    info = json.loads(info.text)

    members = requests.get(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members',
        auth=('api', MAILGUN_API_KEY),
    )
    members = json.loads(members.text)

    return info, members

def create_list(node_id, node_title, contributors):
    requests.post(
        'https://api.mailgun.net/v3/lists',
        auth=('api', MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': node_title + ' Mailing List',
            'access_level': 'members'
        }
    )
    for contrib in contributors:
        contrib.add_to_list(node_id)
    return

def delete_list(node_id):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY)
    )
    return

def add_member(node_id, user_id, email, name, subscribed=True):
    unsub_url = MAILGUN_UNSUB_URL + node_id + '/settings/#configureMailingListAnchor'
    requests.post(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members',
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': subscribed,
            'address': email,
            'name': name,
            'vars': '{"list_unsubscribe": "' + unsub_url + '", "id": "' + user_id + '"}'
        }
    )
    return

def remove_member(node_id, email):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY)
    )
    return

def subscribe(node_id, email):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': True
        }
    )
    return

def unsubscribe(node_id, email):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': False
        }
    )
    return
