from typing import Dict, Any, Union
import operator

import vk

from exceptions import InvalidConfig
from publication import Publication, FileAttach, FileType, Poll
from . import Source


class NeedExpand(Exception):
    adding_line: str

    def __init__(self, add):
        self.adding_line = add


class UnsupportedAttachment(Exception):
    type: str

    def __init__(self, type):
        self.type = type


def add_line(text: str, line: str):
    return text + '\n' + line


@Source.register("vk")
class VKSource(Source):
    token: str
    id: int
    api: vk.API

    def __init__(self, raw: dict):
        self.token = raw['token']
        self.api = vk.API(vk.Session(access_token=self.token), v=5.95)
        id_or_domain = raw['target']
        if isinstance(id_or_domain, str):
            target = self.api.utils.resolveScreenName(screen_name=id_or_domain)
            if target == {}:
                raise InvalidConfig("Target is not exists")
            if target['type'] == 'user':
                self.id = target['object_id']
            elif target['type'] == 'group':
                self.id = -target['object_id']
            else:
                raise InvalidConfig("Target must be user or group")
        else:
            self.id = id_or_domain

    def get(self, after_timestamp: float) -> list:
        posts = self.api.wall.get(owner_id=self.id, count=100, filter='owner')
        posts = filter(lambda p: p['date'] > after_timestamp, posts['items'])
        parsed = []
        for post in posts:
            parsed.append(self.parse_post(post))
        return parsed

    def parse_attachment(self, raw: Dict[str, Any]) -> Union[FileAttach, Poll]:
        type = raw['type']
        object = raw[type]
        if type == 'photo':
            return FileAttach(FileType.PICTURE, link=object['sizes'][-1]['url'])
        if type == 'video':
            video = self.api.video.get(owner_id=object['owner_id'],
                                       videos=[f'{object["owner_id"]}_{object["id"]}_{object["access_key"]}'])['items'][0]
            raise NeedExpand(video['player'])
        if type == 'audio':
            return FileAttach(FileType.AUDIO, link=object['url'])
        if type == 'doc':
            return FileAttach(FileType.CUSTOM, link=object['url'])
        if type == 'link':
            raise NeedExpand(object['url'])
        if type == 'album':
            raise NeedExpand('https://vk.com/album'
                             f'{object["owner_id"]}_{object["id"]}')
        if type == 'poll':
            return Poll(object['question'],
                        list(map(operator.itemgetter('text'), object['answers'])),
                        object['anonymous'],
                        object['multiple']
                        )
        raise UnsupportedAttachment(type)

    def parse_post(self, raw: Dict[str, Any]) -> Publication:
        text = raw['text']
        attachments = []
        for a in raw.get('attachments', []):
            try:
                attachments.append(self.parse_attachment(a))
            except NeedExpand as ex:
                text = add_line(text, ex.adding_line)
            except UnsupportedAttachment as ex:
                id = raw['id']
                owner_id = raw['owner_id']
                original = f"https://vk.com/wall{owner_id}_{id}"
                text = add_line(text, f"Unsupported attachment type '{ex.type}'."
                                      " You may want look to original: "
                                      f"{original}")
        if len(attachments) == 1 and type(attachments[0]) is Poll:
            if text == attachments[0].title:
                text = ''
        return Publication(text, attachments)
