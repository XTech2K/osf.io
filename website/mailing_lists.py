# -*- coding: utf-8 -*-

import requests
import json

from framework import sentry
from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.auth.signals import user_confirmed

from website import settings
from website.util import waterbutler_url_for

from website.settings.local import MAILGUN_API_KEY, MAILGUN_DOMAIN, OWN_URL

def address(node_id):
    return node_id + '@' + MAILGUN_DOMAIN

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
    targets = []
    for _id in subscriptions.keys():
        add_member(node_id, subscriptions[_id], _id)
        targets.append(subscriptions[_id]['email'])
    send_message(node_id, node_title, targets, {
        'subject': "Mailing List Created for " + node_title,
        'text': "A mailing list has been created/enabled for the project " + node_title + "."
    })

def delete_list(node_id):
    requests.delete(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY)
    )

def update_title(node_id, node_title):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id),
        auth=('api', MAILGUN_API_KEY),
        data={
            'name': node_title + ' Mailing List'
        }
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

def update_member(node_id, user, old_email):
    requests.put(
        'https://api.mailgun.net/v3/lists/' + address(node_id) + '/members/' + old_email,
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': user['subscribed'],
            'address': user['email'],
            'name': user['name'],
        }
    )

@queued_task
@app.task
def send_message(node_id, node_title, targets, message):
    requests.post(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN + "/messages",
        auth=("api", MAILGUN_API_KEY),
        data={"from": node_title + " Mailing List <" + address(node_id) + ">",
              "to": targets,
              "subject": message['subject'],
              "text": message['text']})

def check_log_folder(node, user, current_path=None, name_suffix=''):

    if current_path:
        url = waterbutler_url_for('metadata', 'osfstorage', current_path, node, user=user)
        res = requests.get(url)
        res = json.loads(res.text)
        if 'data' in res.keys():
            return current_path, name_suffix

    url = waterbutler_url_for('create_folder', 'osfstorage', '/Mailed Attachments/', node, user=user)
    res = requests.post(url)
    res = json.loads(res.text)

    if res.get('path'):
        return res.get('path'), ''

    else:
        created=False
        i = 0
        while not created:
            i += 1
            url = waterbutler_url_for('create_folder', 'osfstorage', '/Mailed Attachments({})/'.format(str(i)), node, user=user)
            res = requests.post(url)
            res = json.loads(res.text)
            if res.get('path'):
                created=True

        name_suffix = '({})'.format(str(i)) if i else ''
        return res.get('path'), name_suffix

def upload_attachment(attachment, node, user, folder_path):
    attachment.seek(0)
    name = folder_path + (attachment.filename or settings.MISSING_FILE_NAME)
    content = attachment.read()
    upload_url = waterbutler_url_for('upload', 'osfstorage', name, node, user=user)

    requests.put(
        upload_url,
        data=content,
    )

@queued_task
@app.task
def update_list(node_id, node_title, node_has_list, subscriptions):
    info, members = get_list(node_id)

    if node_has_list:

        if 'list' in info.keys():
            info = info['list']
            members = members['items']
            list_members = {}
            for member in members:
                list_members[member['vars']['id']] = {
                    'subscribed': member['subscribed'],
                    'email': member['address'],
                    'name': member['name']
                }
            if info['name'] != node_title + ' Mailing List':
                update_title(node_id, node_title)

            ids_to_add = set(subscriptions.keys()).difference(set(list_members.keys()))
            for contrib_id in ids_to_add:
                add_member(node_id, subscriptions[contrib_id], contrib_id)

            ids_to_remove = set(list_members.keys()).difference(set(subscriptions.keys()))
            for member_id in ids_to_remove:
                remove_member(node_id, list_members[member_id]['address'])
                del list_members[member_id]

            for member_id in list_members.keys():
                if list_members[member_id] != subscriptions[member_id]:
                    update_member(node_id, subscriptions[member_id], list_members[member_id]['email'])

        else:
            create_list(node_id, node_title, subscriptions)
            return

    else:

        if 'list' in info.keys():
            delete_list(node_id)
