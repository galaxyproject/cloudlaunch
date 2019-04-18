FROM ubuntu:18.04 as stage1

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1

RUN set -xe; \
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
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* \
    && mkdir -p /app \
    && pip3 install virtualenv \
    && virtualenv -p python3 --prompt "(cloudlaunch)" /app/venv

# Set working directory to /app/
WORKDIR /app/

# Add files to /app/
ADD . /app

# Install requirements. Move this above ADD as 'pip install cloudlaunch-server'
# asap so caching works
RUN /app/venv/bin/pip3 install -U pip && /app/venv/bin/pip3 install --no-cache-dir -r requirements.txt

RUN cd django-cloudlaunch && /app/venv/bin/python manage.py collectstatic --no-input


# Stage-2
FROM ubuntu:18.04

# Create cloudlaunch user environment
RUN useradd -ms /bin/bash cloudlaunch \
    && mkdir -p /app \
    && chown cloudlaunch:cloudlaunch /app -R \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        git-core \
        python-psycopg2 \
        python3-pip \
        python3-setuptools \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

WORKDIR /app/

# Copy cloudlaunch files to final image
COPY --chown=cloudlaunch:cloudlaunch --from=stage1 /app /app

RUN chmod a+x /app/venv/bin/*

# Switch to new, lower-privilege user
USER cloudlaunch

# gunicorn will listen on this port
EXPOSE 8000

CMD /app/venv/bin/gunicorn -b :8000 --access-logfile - --error-logfile - --log-level debug cloudlaunchserver.wsgi
