"""Amazon CloudWatch Logs."""

import logging
import time

from boto.logs import connect_to_region
from boto.logs.exceptions import \
    InvalidSequenceTokenException, \
    ResourceAlreadyExistsException


class CloudWatchLogsConnection(object):

    def __init__(self, region, key=None, secret=None):
        self.connection = connect_to_region(
            region,
            aws_access_key_id=key,
            aws_secret_access_key=secret)

    def handler(self, group, stream):
        try:
            self.connection.create_log_group(group)
        except ResourceAlreadyExistsException:
            pass
        try:
            self.connection.create_log_stream(group, stream)
        except ResourceAlreadyExistsException:
            pass
        return Handler(self.connection, group, stream)


class Handler(logging.Handler):

    def __init__(self, connection, group, stream, *args, **kwargs):
        super(Handler, self).__init__(*args, **kwargs)
        self.connection = connection
        self.group = group
        self.stream = stream
        self.token = None
        self.events = []

    def emit(self, record):
        self.events.append({
            'timestamp': int(record.created * 1000),
            'message': self.format(record),
        })

    def flush(self):
        if not self.events:
            return
        for _ in range(6):
            try:
                try:
                    response = self.connection.put_log_events(
                        self.group, self.stream, self.events, self.token)
                except InvalidSequenceTokenException as ex:
                    self.token = ex.body['expectedSequenceToken']
                    response = self.connection.put_log_events(
                        self.group, self.stream, self.events, self.token)
                self.token = response['nextSequenceToken']
                self.events = []
                break
            except Exception:
                time.sleep(30)
