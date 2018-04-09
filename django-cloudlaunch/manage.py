#!/usr/bin/env python
import os
import sys
import signal

# The integration test script sends a SIGINT to terminate the django server
# after the tests are complete. Handle the SIGINT here and terminate
# gracefully, or coverage will terminate abruptly without writing the
# .coverage file
def test_signal_handler(*args, **kwargs):
    sys.exit(0)

signal.signal(signal.SIGINT, test_signal_handler)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudlaunchserver.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
