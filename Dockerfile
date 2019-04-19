FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1

RUN set -xe; \
    useradd -ms /bin/bash cloudlaunch; \
    apt-get -qq update && apt-get install -y --no-install-recommends \
        apt-transport-https \
        git-core \
        make \
        software-properties-common \
        gcc \
        python3-dev \
        libffi-dev \
        libpq-dev \
        python-psycopg2 \
        python3-pip \
        python3-setuptools \
    && mkdir -p /app \
    # Set Python 3 as the default Python installation
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.6 1

# Set working directory to /app/
WORKDIR /app/

# Add files to /app/
ADD . /app

# Install requirements. Move this above ADD as 'pip install cloudlaunch-server'
# asap so caching works
RUN pip3 install -U pip && pip install --no-cache-dir -r requirements.txt \
    && cd django-cloudlaunch && python manage.py collectstatic --no-input \
    && apt-get remove -y make \
        software-properties-common \
        gcc \
        python3-dev \
        libffi-dev \
        libpq-dev \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* \
    && chown cloudlaunch:cloudlaunch -R /app

# Switch to new, lower-privilege user
USER cloudlaunch

# gunicorn will listen on this port
EXPOSE 8000

CMD gunicorn -k gevent -b :8000 --access-logfile - --error-logfile - --log-level debug cloudlaunchserver.wsgi
