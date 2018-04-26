FROM python:3.6-alpine

ENV PYTHONUNBUFFERED 1

RUN apk update \
    # psycopg2 dependencies
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql-dev \
    # CFFI dependencies
    && apk add libffi-dev openssl-dev py-cffi \
    # git for cloning requirements dependencies
    && apk add git \
    # For pynacl
    && apk add make linux-headers

# Create cloudlaunch user environment
RUN adduser -D -g '' cloudlaunch \
    && mkdir -p /app

# Switch to new, lower-privilege user
USER cloudlaunch

# Set working directory to /app/
WORKDIR /app/

# Add files to /app/
ADD . /app

# Install requirements. Move this above ADD as 'pip install cloudlaunch-server'
# asap so caching works
RUN pip install --no-cache-dir -r requirements.txt

#RUN python django-cloudlaunch/manage.py collectstatic --no-input

# Change ownership to cloudlaunch
RUN chown -R cloudlaunch:cloudlaunch /app

# gunicorn will listen on this port
EXPOSE 8000

CMD gunicorn -b :8000 --access-logfile - --error-logfile - --log-level debug cloudlaunchserver.wsgi