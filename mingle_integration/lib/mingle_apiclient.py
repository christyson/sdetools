import urllib
import urllib2
import base64

from sdelib.apiclient import APIBase
from xml.dom import minidom
import logging
logger = logging.getLogger(__name__)

class MingleAPIBase(APIBase):
    def __init__(self, config):
        self.config = config
        self.base_uri = '%s://%s/api/v2/projects/%s' % (self.config['method'],
                self.config['alm_server'], self.config['alm_project'])
        handler_func = (urllib2.HTTPSHandler if self.config['method'] == 'https'
                        else urllib2.HTTPHandler)
        handler = handler_func(debuglevel=0)
        self.opener = urllib2.build_opener(handler)

    def call_api(self, target, method=self.URLRequest.GET, args=None):
        """
        Internal method used to call a RESTFul API

        Keywords:
        target - the path of the API call (without host name)
        method -  HTTP Verb, specified by the URLRequest class. Default
                  is GET
        args - A dictionary of post paramters in format
               { 'key1':'value1', 'key2':'value2'}
        """
        logger.info('Calling API: %s %s' % (method, target))
        logger.debug('    Args: %s' % ((repr(args)[:200]) + (repr(args)[200:] and '...')))
        req_url = '%s/%s' % (self.base_uri, target)
        args = args or {}
        data = None
        if method == self.URLRequest.GET:
            if args:
                req_url = '%s?%s' % (req_url, urllib.urlencode(args))
        else:
            encoded_args = dict((key.encode('utf-8'), val.encode('utf-8')) for key, val in args.items())
            data = urllib.urlencode(encoded_args)
        req = self.URLRequest(req_url, data=data, method=method)
        encoded_auth = base64.encodestring('%s:%s' % (self.config['alm_user'], self.config['alm_pass']))[:-1]
        authheader =  "Basic %s" % (encoded_auth)
        req.add_header("Authorization", authheader)

        call_success = True
        try:
            handle = self.opener.open(req)
        except IOError, e:
            handle = e
            call_success = False

        if not call_success:
            if not hasattr(handle, 'code'):
                raise self.ServerError('Invalid server or server unreachable.')
            try:
                err_ret = handle.read()
            except:
                pass
            if handle.code == 401 or handle.code == 404:
                raise self.APIAuthError
            raise self.APICallError(handle.code, err_ret)

        result = ''
        while True:
            res_buf = handle.read()
            if not res_buf:
                break
            result += res_buf
        handle.close()

        try:
            if result:
                result = minidom.parseString(result)
        except Exception, err:
            #This means that the result doesn't have XML, not an error
            pass
        return result
