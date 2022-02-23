# -*- coding: utf-8 -*-

import os
import logging
import tempfile
import _thread
import queue
from contextlib import contextmanager
import requests

logger = logging.getLogger(__name__)


def download_file(url, fpath, token=''):
    logger.debug('starting to fetch %s', url)
    headers = {"Authorization": f"Bearer {token}"} if token else None
    req = requests.get(url, stream=True, headers=headers)
    with open(fpath, 'wb') as file_handle:
        for chunk in req.iter_content(chunk_size=1024*64):
            if chunk:  # filter out keep-alive new chunks
                file_handle.write(chunk)
                file_handle.flush()
    logger.debug('fetch %s', fpath)
    return fpath


@contextmanager
def create_tmp_file(content=''):
    _fd, name = tempfile.mkstemp()
    try:
        if content:
            os.write(_fd, content)
        yield name
    finally:
        os.close(_fd)
        os.remove(name)


class WorkerPool:
    def __init__(self, func, nworker=10):
        self.nworker = nworker
        self.func = func
        self.queue = queue.Queue()

    def start(self):
        for __ in range(self.nworker):
            _thread.start_new_thread(self.do_work, tuple())

    def add_task(self, msg):
        self.queue.put(msg)

    def do_work(self):
        while True:
            msg = self.queue.get()
            self.func(msg)


def get_http_proxy(environ):
    proxy, proxy_port, no_proxy = None, None, None

    if 'http_proxy' in environ:
        http_proxy = environ['http_proxy']
        prefix = 'http://'
        if http_proxy.startswith(prefix):
            http_proxy = http_proxy[len(prefix):]
        proxy, proxy_port = http_proxy.split(':')

    if 'no_proxy' in environ:
        no_proxy = environ['no_proxy']

    return proxy, proxy_port, no_proxy
