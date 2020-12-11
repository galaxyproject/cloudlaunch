FROM ubuntu:20.04 as stage1

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
        python3-pip \
        python3-setuptools \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* \
    && mkdir -p /app \
    && pip3 install virtualenv \
    && virtualenv -p python3 --prompt "(cloudlaunch)" /app/venv

# Set working directory to /app/
WORKDIR /app/

# Only add files required for installation to improve build caching
ADD requirements.txt /app
ADD setup.py /app
ADD README.rst /app
ADD HISTORY.rst /app
ADD django-cloudlaunch/cloudlaunchserver/__init__.py /app/django-cloudlaunch/cloudlaunchserver/__init__.py

# Install requirements. Move this above ADD as 'pip install cloudlaunch-server'
# asap so caching works
RUN /app/venv/bin/pip3 install -U pip && /app/venv/bin/pip3 install --no-cache-dir -r requirements.txt

# Stage-2
FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

# Create cloudlaunch user environment
RUN useradd -ms /bin/bash cloudlaunch \
    && mkdir -p /app \
    && chown cloudlaunch:cloudlaunch /app -R \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        git-core \
        python3-pip \
        python3-setuptools \
        locales \
    && locale-gen $LANG && update-locale LANG=$LANG \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* \

WORKDIR /app/

# Copy cloudlaunch files to final image
COPY --chown=cloudlaunch:cloudlaunch --from=stage1 /app /app

# Add the source files last to minimize layer cache invalidation
ADD --chown=cloudlaunch:cloudlaunch . /app

# Switch to new, lower-privilege user
USER cloudlaunch

RUN cd django-cloudlaunch \
    && /app/venv/bin/python manage.py collectstatic --no-input

# gunicorn will listen on this port
EXPOSE 8000

CMD /bin/bash -c "source /app/venv/bin/activate && /app/venv/bin/gunicorn -k gevent -b :8000 --access-logfile - --error-logfile - --log-level info cloudlaunchserver.wsgi"
