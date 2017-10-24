"""Plugin implementation for a simple web application."""
import logging
import time
import requests
import requests.exceptions
from .base_vm_app import BaseVMAppPlugin

log = logging.getLogger(__name__)


class SimpleWebAppPlugin(BaseVMAppPlugin):
    """
    Implementation for an appliance exposing a web interface.

    The implementation is based on the Base VM app except that it expects
    a web frontend.
    """

    def __init__(self):
        """Init any base app vars."""
        self.base_app = False

    def wait_for_http(self, url, ok_status_codes=None, max_retries=200,
                      poll_interval=5):
        """
        Wait till app is responding at http URL.

        :type ok_status_codes: ``list`` of int
        :param ok_status_codes: List of HTTP status codes that are considered
                                OK by the appliance. Code 200 is assumed.
        """
        if ok_status_codes is None:
            ok_status_codes = [401, 403]
        count = 0
        while count < max_retries:
            time.sleep(poll_interval)
            try:
                r = requests.head(url)
                r.raise_for_status()
                return
            except requests.exceptions.HTTPError as http_exc:
                if http_exc.response.status_code in ok_status_codes:
                    return
            except requests.exceptions.ConnectionError:
                pass
            count += 1

    def launch_app(self, provider, task, name, cloud_config,
                   app_config, user_data, **kwargs):
        """
        Handle the app launch process and wait for http.

        Pass boolean ``check_http`` as a ``False`` kwarg if you don't
        want this method to perform the app http check and prefer to handle
        it in the child class.
        """
        result = super(SimpleWebAppPlugin, self).launch_app(
            provider, task, name, cloud_config, app_config, user_data)
        check_http = kwargs.get('check_http', True)
        if check_http and result.get('cloudLaunch', {}).get('publicIP'):
            log.info("Simple web app going to wait for http")
            result['cloudLaunch']['applicationURL'] = \
                'http://%s/' % result['cloudLaunch']['publicIP']
            task.update_state(
                state='PROGRESSING',
                meta={"action": "Waiting for application to become ready at %s"
                                % result['cloudLaunch']['applicationURL']})
            log.info("Waiting on http at %s",
                     result['cloudLaunch']['applicationURL'])
            self.wait_for_http(result['cloudLaunch']['applicationURL'],
                               ok_status_codes=[], max_retries=200,
                               poll_interval=5)
        else:
            result['cloudLaunch']['applicationURL'] = 'N/A'
        return result
