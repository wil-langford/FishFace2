import django.conf.urls as dcu
import djff.views as views
urlpatterns = dcu.patterns(
    '',
    # TODO: is this some sort of orphan?  check.
    # dcu.url(
    #     r'^hc/image_upload/(?P<chain_id>\d+)/$',
    #     views.image_capturer,
    #     name='image_capturer'
    # ),
    dcu.url(
        r'^upload_imagery/$',
        views.image_capturer,
        name='image_capturer'
    ),
    dcu.url(
        r'^imagery_request/$',
        views.experiment_capturer,
        name='experiment_capturer'
    ),

    dcu.url(r'^$', views.index, name='index'),

    dcu.url(
        r'^xp/$',
        views.experiment_index,
        name='experiment_index'
    ),
    dcu.url(
        r'^xp/rename/(?P<xp_id>\d+)/$',
        views.experiment_rename,
        name='experiment_rename'
    ),
    dcu.url(
        r'^xp/renamer/(?P<xp_id>\d+)/$',
        views.experiment_renamer,
        name='experiment_renamer'
    ),
    dcu.url(
        r'^xp/capture/(?P<xp_id>\d+)/$',
        views.experiment_capture,
        name='experiment_capture'
    ),
    dcu.url(
        r'^xp/new/$',


        views.experiment_new,
        name='experiment_new'
    ),

    dcu.url(
        r'^hc/$',
        views.hopperchain_index,
        name='hopperchain_index'
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
        views.hopperchain_delete_hopper,
        name='hopperchain_delete_hopper'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/insert/(?P<hopper_index>\d+)/$',
        views.hopperchain_insert_hopper,
        name='hopperchain_insert_hopper'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/editor/$',
        views.hopperchain_editor,
        name='hopperchain_editor'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/up/(?P<hopper_index>\d+)/$',
        views.hopperchain_up,
        name='hopperchain_up'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/down/(?P<hopper_index>\d+)/$',
        views.hopperchain_down,
        name='hopperchain_down'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/set/(?P<hopper_index>\d+)/(?P<hop_type>\w+)/$',
        views.hopperchain_set,
        name='hopperchain_set'
    ),
    dcu.url(
        r'^hc/edit/(?P<chain_id>\d+)/$',
        views.hopperchain_edit,
        name='hopperchain_edit'
    ),
    dcu.url(
        r'^hc/deleter/(?P<chain_id>\d+)/$',
        views.hopperchain_deleter,
        name='hopperchain_deleter'
    ),
    dcu.url(
        r'^hc/new/$',
        views.hopperchain_new,
        name='hopperchain_new'
    ),
    dcu.url(
        r'^hc/preview/(?P<chain_id>\d+)/preview.jpg$',
        views.hopperchain_preview_image,
        name='hopperchain_preview_image'
    ),

    dcu.url(
        r'^cj/list/$',
        views.CaptureJobIndex.as_view(),
        name='cj_list',
    ),
    dcu.url(
        r'^cj/add/$',
        views.CaptureJobCreate.as_view(),
        name='cj_add'
    ),
    dcu.url(
        r'^cj/(?P<pk>\d+)/$',
        views.CaptureJobUpdate.as_view(),
        name='cj_update'
    ),
    dcu.url(
        r'^cj/(?P<pk>\d+)/delete/$',
        views.CaptureJobDelete.as_view(),
        name='cj_delete'
    ),
)


