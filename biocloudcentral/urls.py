import settings
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', 'biocloudcentral.views.home', name='home'),
    url(r'^launch$', 'biocloudcentral.views.launch', name='launch'),
    url(r'^launch-status$', 'biocloudcentral.views.launch_status', name='launch_status'),
    url(r'^monitor$', 'biocloudcentral.views.monitor', name='monitor'),
    url(r'^ud$', 'biocloudcentral.views.userdata', name='ud'),
    url(r'^kp$', 'biocloudcentral.views.keypair', name='kp'),
    url(r'^state$', 'biocloudcentral.views.instancestate', name='inst_state'),
    url(r'^dynamic-fields$', 'biocloudcentral.views.dynamicfields', name='dynamic_fields'),
    url(r'^get-flavors$', 'biocloudcentral.views.get_flavors', name='get_flavors'),
    url(r'^get-placements$', 'biocloudcentral.views.get_placements', name='get_placements'),
    url(r'^get-key-pairs$', 'biocloudcentral.views.get_key_pairs', name='get_key_pairs'),
    url(r'^fetch-clusters$', 'biocloudcentral.views.fetch_clusters', name='fetch_clusters'),
    url(r'^update-clusters$', 'biocloudcentral.views.update_clusters',
        name='update_clusters'),
    url(r'^revoke-fetch-clusters$', 'biocloudcentral.views.revoke_fetch_clusters',
        name='revoke_fetch_clusters'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # Include CBLtweaker app
    # url(r'^cbltweaker', include('biocloudcentral.cbltweaker.urls')),

    # Needed to serve static content collected via `collectstatic`
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATICFILES_DIRS[0], 'show_indexes': True}),
)
