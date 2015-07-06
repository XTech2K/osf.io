# -*- coding: utf-8 -*-

import requests
import json

from framework import sentry
from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.auth.signals import user_confirmed

from website import settings

from website.settings.local import MAILGUN_API_KEY, OWN_URL

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

def create_list(node_id, node_title, subscriptions):
    requests.post(
        'https://api.mailgun.net/v3/lists',
        auth=('api', MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': node_title + ' Mailing List',
            'access_level': 'members'
        }
    )
    for _id in subscriptions.keys():
        add_member(node_id, subscriptions[_id], _id)

def delete_list(node_id):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY)
    )

def add_member(node_id, user, user_id):
    unsub_url = OWN_URL + node_id + '/settings/#configureMailingListAnchor'
    requests.post(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members',
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': user['subscribed'],
            'address': user['email'],
            'name': user['name'],
            'vars': '{"list_unsubscribe": "' + unsub_url + '", "id": "' + user_id + '"}'
        }
    )

def remove_member(node_id, email):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY)
    )

def subscribe(node_id, email):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': True
        }
    )

def unsubscribe(node_id, email):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': False
        }
    )

@queued_task
@app.task
def update_list(node_id, node_title, node_has_list, subscriptions):
    contrib_ids = subscriptions.keys()

    info, members = get_list(node_id)

    if node_has_list:

        if 'list' in info.keys():
            info = info['list']
            members = members['items']
            member_ids = [member['vars']['id'] for member in members]

            if info['name'] != node_title:
                pass

            for contrib_id in contrib_ids:
                if contrib_id not in member_ids:
                    add_member(node_id, subscriptions[contrib_id], contrib_id)


            for member in members:
                if member['vars']['id'] not in subscriptions.keys():
                    remove_member(node_id, member['address'])
                elif member['subscribed'] != subscriptions[member['vars']['id']]['subscribed']:
                    if member['subscribed'] == False:
                        subscribe(node_id, member['address'])
                    else:
                        unsubscribe(node_id, member['address'])

        else:
            create_list(node_id, node_title, subscriptions)
            return

    else:

        if 'list' in info.keys():
            delete_list(node_id)
