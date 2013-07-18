from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'cbltweaker.views.home', name='cbltweaker'),
)
