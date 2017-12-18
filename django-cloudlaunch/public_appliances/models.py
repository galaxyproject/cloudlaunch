import requests

from django.db import models

from django_countries.fields import CountryField

from djcloudbridge import models as cb_models

from urllib.parse import urlparse
from django.core.exceptions import ObjectDoesNotExist


### PublicServer Models ###
class Tag(models.Model):
    """
    Tag referencing a keyword for search features
    """
    name = models.TextField(primary_key=True)


class Sponsor(models.Model):
    """
    A Sponsor is defined by his name and his link url.
    Directly inspired by https://wiki.galaxyproject.org/PublicGalaxyServers Sponsor(s) part
    """
    name = models.TextField()
    url = models.URLField(null=True)

    def __str__(self):
        return "{0}".format(self.name)


class Location(models.Model):
    """
    A location containing the latitude and longitude (fetched from the ip) and
    a django_country https://github.com/SmileyChris/django-countries
    """
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    city = models.TextField(blank=True, null=True)

    country = CountryField(blank='(select country)')

    def __str__(self):
        return "Country: {0}, Latitude: {1}, Longitude: {2}".format(self.country,
                                                                    self.latitude,
                                                                    self.longitude,
                                                                    self.city)


class PublicService(cb_models.DateNameAwareModel):
    """
    Public Service class to display the public services available,
    for example, on https://wiki.galaxyproject.org/PublicGalaxyServers
    The fields have been inspired by this public galaxy page
    """
    slug = models.SlugField(max_length=100, primary_key=True)
    links = models.URLField()
    location = models.ForeignKey(Location, on_delete=models.CASCADE, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    email_user_support = models.EmailField(blank=True, null=True)
    quotas = models.TextField(blank=True, null=True)
    sponsors = models.ManyToManyField(Sponsor, blank=True)
    # Featured links means a more important link to show "first"
    featured = models.BooleanField(default=False)
    # The referenced application, if existing
    # application = models.ForeignKey(Application, on_delete=models.CASCADE, blank=True, null=True)
    # The url link to the logo of the Service
    logo = models.URLField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return "{0}".format(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)

        # Construct the API to find geolocation from ip
        api_hostname = 'http://ip-api.com'
        return_format = 'json'
        parsed_url = urlparse(self.links)
        netloc = parsed_url.netloc
        geolocation_api = '{0}/{1}/{2}'.format(api_hostname, return_format, netloc)

        response = requests.get(geolocation_api)
        if  response.status_code != 200:
            raise Exception("Couldn't find the geolocation from ip {0}: {1}".format(geolocation_api, response.status_code))
        # Construct or get the Location
        json_geoloc = response.json()
        self.location = Location.objects.get_or_create(longitude=json_geoloc["lon"],
                                    latitude=json_geoloc["lat"],
                                    defaults={
                                        'country': json_geoloc["countryCode"],
                                        'city': json_geoloc["city"],
                                    },)[0]

        super(PublicService, self).save(*args, **kwargs)
