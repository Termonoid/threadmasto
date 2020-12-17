from typing import List, Optional
from tempfile import NamedTemporaryFile
from enum import IntEnum

import requests

class AttachmentType(IntEnum):
    AUDIO = 1
    PICTURE = 2
    VIDEO = 3
    CUSTOM = 4
    POLL = 5


class Attachment:
    link: Optional[str]
    _file_name: Optional[str]
    _fd = None

    def __init__(self,
                 link: Optional[str] = None,
                 file_name: Optional[str] = None):

        if bool(link) == bool(file_name):
            raise ValueError("Link OR path. Not both, not none")
        self.link = link
        self._file_name = file_name

    def _download(self):
        if self.link and not self._fd:
            self._fd = NamedTemporaryFile()
            r = requests.get(self.link, stream=True)
            for chunk in r.iter_content(chunk_size=4096):
                self._fd.write(chunk)
            self._fd.seek(0)
            self._file_name = self._fd.name

    @property
    def file_name(self):
        if not self._file_name:
            self._download()
        return self._file_name

    @property
    def fd(self):
        if self._fd:
            return self._fd
        if self._file_name and not self.link:
            return open(self._file_name)
        else:
            self._download()
            return self.fd

class Publication:
    plain_text: str
    attachments: List[Attachment]

    def __init__(self, text, attachments):
        ...
