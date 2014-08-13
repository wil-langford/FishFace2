import django.conf.urls as dcu
import djff.views as views

urlpatterns = dcu.patterns(
    '',
    dcu.url(r'^$', views.index, name='index'),
    dcu.url(
        r'^hc/$',
        views.hopperchain_index,
        name='hopperchain_index'
    ),
    dcu.url(
        r'^hc/(?P<chain_id>\d+)/$',
        views.hopperchain_detail,
        name='hopperchain_detail'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/$',
        views.hopperchain_edit,
        name='hopperchain_edit'
    ),
    dcu.url(
        r'^hc/rename/(?P<chain_id>\d+)/$',
        views.hopperchain_rename,
        name='hopperchain_rename'
    ),
    dcu.url(
        r'^hc/renamer/(?P<chain_id>\d+)/$',
        views.hopperchain_renamer,
        name='hopperchain_renamer'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/delete/(?P<hopper_index>\d+)/$',
        views.hopperchain_delete,
        name='hopperchain_delete'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/insert/(?P<hopper_index>\d+)/$',
        views.hopperchain_insert,
        name='hopperchain_insert'
    ),
)