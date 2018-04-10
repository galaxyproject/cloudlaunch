#!/usr/bin/env python
import os
import sys
import signal


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudlaunchserver.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
