# -*- coding: utf-8 -*-

import requests
import json

from framework import sentry
from framework.tasks import app
from framework.auth.core import User
from framework.tasks.handlers import queued_task
from framework.auth.signals import user_confirmed

from framework.transactions.context import transaction

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
        add_member(node_id, contrib)

def delete_list(node_id):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY)
    )

def add_member(node_id, user):
    unsub_url = OWN_URL + node_id + '/settings/#configureMailingListAnchor'
    requests.post(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members',
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': user.project_mailing_lists[node_id],
            'address': user.email,
            'name': user.display_full_name(),
            'vars': '{"list_unsubscribe": "' + unsub_url + '"}'
        }
    )


def remove_member(node_id, user):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + user.email,
        auth=('api', MAILGUN_API_KEY)
    )
    user.save()

def subscribe(node_id, user):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + user.email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': True
        }
    )
    user.project_mailing_lists[node_id] = True
    user.save()

def unsubscribe(node_id, user):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + user.email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': False
        }
    )
    user.project_mailing_lists[node_id] = False
    user.save()

@queued_task
@app.task
@transaction()
def update_list(node_id, node_title, node_has_list, contrib_ids):
    contributors = [User.load(contrib_id) for contrib_id in contrib_ids]

    info, members = get_list(node_id)

    if node_has_list:

        if 'list' in info.keys():
            info = info['list']
            members = members['items']
            member_ids = [member['vars']['id'] for member in members]

            if info['name'] != node_title:
                pass

            for contrib in contributors:
                if contrib._id not in member_ids:
                    contrib.add_to_list(node_id)

            for member in members:
                if member['vars']['id'] not in contrib_ids:
                    remove_member(node_id, member['address'])

        else:
            create_list(node_id, node_title, contributors)
            return

    else:

        if 'list' in info.keys():
            delete_list(node_id)
