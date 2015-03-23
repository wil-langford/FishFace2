import django.conf as dc
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    # Examples:
    # url(r'^$', 'django_fishface.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'djff.views.xp_index', name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^fishface/', include('djff.urls', namespace='djff')),
)


# TODO: for development only - remove before production
if dc.settings.DEBUG:
    urlpatterns += patterns(
        '',
        (
            r'^media/(?P<path>.*)$',
            'django.views.static.serve',
            {
                'document_root': dc.settings.MEDIA_ROOT,
                'show_indexes': True
            }
        ),
    )