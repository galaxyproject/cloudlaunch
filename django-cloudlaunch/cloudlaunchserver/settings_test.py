"""
Django settings used during cloudlaunch testing
"""
import signal

# The integration test script sends a SIGINT to terminate the django server
# after the tests are complete. Handle the SIGINT here and terminate
# gracefully, or coverage will terminate abruptly without writing the
# .coverage file
def test_signal_handler(*args, **kwargs):
    sys.exit(0)
signal.signal(signal.SIGINT, test_signal_handler)

from cloudlaunchserver.settings import *  # noqa


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/cloudlaunch_testdb.sqlite3',
    }
}
