FROM python:3.6-alpine

ENV PYTHONUNBUFFERED 1

RUN apk update \
  # psycopg2 dependencies
  && apk add --virtual build-deps gcc python3-dev musl-dev \
  && apk add postgresql-dev

# Requirements are installed here to ensure they will be cached.
RUN mkdir -p /app
ADD requirements_dev.txt /app/requirements.txt

# Set working directory to /app/
WORKDIR /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create unprivileged user
RUN adduser --disabled-password --gecos '' cloudlaunch

# Add files to /app/
# This should probably be mounted at deployment step
ADD ./django-cloudlaunch /app
RUN chown -R cloudlaunch:cloudlaunch /app

# gunicorn will listen on this port
EXPOSE 8000

# Collect static files
RUN python manage.py collectstatic --noinput

CMD gunicorn -b :8000 django-cloudlaunch/cloudlaunchserver.wsgi