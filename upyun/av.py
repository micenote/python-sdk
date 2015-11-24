# -*- coding: utf-8 -*-

import json
import base64
import ast

from .modules.httpipe import UpYunHttp
from .modules.compat import urlencode, b
from .modules.exception import UpYunClientException, UpYunServiceException
from .modules.sign import make_content_md5, decode_msg

class AvPretreatment(object):
    HOST = 'p0.api.upyun.com'
    PRETREAT = '/pretreatment/'
    STATUS = '/status/'

    def __init__(self, bucket, operator, password, chunksize, timeout):
        self.bucket = bucket
        self.operator = operator
        self.password = password
        self.chunksize = chunksize
        self.timeout = timeout
        self.hp = UpYunHttp(self.timeout)

    # --- public API
    def pretreat(self, tasks, source, notify_url=''):
        data = {'bucket_name': self.bucket, 'source': source,
                'notify_url': notify_url, 'tasks': tasks,}
        return self.__requests_pretreatment(data)

    def status(self, taskids):
        data = {}
        if type(taskids) == str:
            taskids = taskids.split(',')
        if type(taskids) == list and len(taskids) <= 20:
            taskids = ','.join(taskids)
        else:
            raise UpYunClientException('length of taskids should less than 20')

        data['bucket_name'] = self.bucket
        data['task_ids'] = taskids
        content = self.__requests_status(data)
        if type(content)  == dict and 'tasks' in content:
            return content['tasks']
        raise UpYunServiceException(None, 500,
                        'Servers except respond tasks list', 'Service Error')

    # --- private API
    def __requests_pretreatment(self, data):
        method = 'POST'
        tasks = data['tasks']
        assert isinstance(tasks, list)
        data['tasks'] = decode_msg(base64.b64encode(b(json.dumps(tasks))))

        uri = self.PRETREAT
        signature = self.__create_signature(data)
        auth = 'UPYUN %s:%s' % (self.operator, signature)
        headers = {'Authorization': auth,
                   'Content-Type': 'application/x-www-form-urlencoded'}
        value = urlencode(data)
        resp = self.hp.do_http_pipe(method, self.HOST, uri,
                                    headers=headers, value=value)
        return self.__handle_resp(resp, method)

    def __requests_status(self, data):
        method = 'GET'
        signature = self.__create_signature(data)
        data = urlencode(data)
        uri = '%s?%s' % (self.STATUS, data)
        auth = 'UPYUN %s:%s' % (self.operator, signature)
        headers = {'Authorization': auth}
        resp = self.hp.do_http_pipe(method, self.HOST, uri, headers=headers)
        return self.__handle_resp(resp, method)

    def __handle_resp(self, resp, method):
        content = None
        try:
            content = resp.json()
        except Exception as e:
            raise UpYunClientException(str(e))
        return content

    def __create_signature(self, metadata):
        assert isinstance(metadata, dict)
        signature = ''.join(map(lambda kv: '%s%s' %
                (kv[0], kv[1] if type(kv[1]) != list else ''.join(kv[1])),
                sorted(metadata.items())))
        signature = '%s%s%s' % (self.operator, signature, self.password)
        return make_content_md5(b(signature))

# --- Signature not correct right now
class CallbackValidation(object):
    KEYS = ['bucket_name',
            'status_code',
            'path',
            'description',
            'task_id',
            'info',
            'signature',
            ]

    def __init__(self, av):
        self.av = av

    def verify_sign(self, value):
        assert isinstance(value, dict)
        value = self.__set_params_by_post(value)
        if data.has_key('signature'):
            signature = data['signature']
            del data['signature']
            if signature == self.av.__create_signature(data):
                return True
        return False

    def __set_params_by_post(self, value):
        data = {}
        for k in KEYS:
            if k in value:
                v = value[k]
                if isinstance(v, list):
                    v = ' '.join(value)
                data[k] = v
        return data