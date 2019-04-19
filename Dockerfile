FROM ubuntu:18.04 as stage1

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
RUN pip3 install -U pip && pip install --no-cache-dir -r requirements.txt

RUN cd django-cloudlaunch && python manage.py collectstatic --no-input

# Stage-2
FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED 1

# Create CloudLaunch user environment
RUN useradd -ms /bin/bash cloudlaunch \
    && mkdir -p /app \
    && chown cloudlaunch:cloudlaunch /app -R \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        git-core \
        python-psycopg2 \
        python3-pip \
        python3-setuptools \
    # Remove Python 2
    && apt remove -y python \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* \
    # Set Python 3 as the default Python installation
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.6 1

WORKDIR /app/

# Copy CloudLaunch files to final image
COPY --chown=cloudlaunch:cloudlaunch --from=stage1 /app /app
COPY --from=stage1 /usr/local/bin /usr/local/bin
# Copy Python modules
COPY --from=stage1 /usr/local/lib/python3.6/dist-packages /usr/local/lib/python3.6/dist-packages
# We may only need libpq.so* files but can't copy multiple files w/ COPY
COPY --from=stage1 /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

# Switch to new, lower-privilege user
USER cloudlaunch

# gunicorn will listen on this port
EXPOSE 8000

CMD gunicorn -k gevent -b :8000 --access-logfile - --error-logfile - --log-level debug cloudlaunchserver.wsgi
