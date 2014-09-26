import django.conf.urls as dcu
import djff.views as views
urlpatterns = dcu.patterns(
    '',
    dcu.url(
        r'^upload_imagery/$',
        views.image_capturer,
        name='image_capturer'
    ),
    dcu.url(
        r'^imagery_request/$',
        views.xp_capturer,
        name='xp_capturer'
    ),

    dcu.url(r'^$', views.index, name='index'),

    dcu.url(
        r'^xp/$',
        views.xp_index,
        name='xp_index'
    ),
    dcu.url(
        r'^xp/rename/(?P<xp_id>\d+)/$',
        views.xp_rename,
        name='xp_rename'
    ),
    dcu.url(
        r'^xp/renamer/(?P<xp_id>\d+)/$',
        views.xp_renamer,
        name='xp_renamer'
    ),
    dcu.url(
        r'^xp/capture/(?P<xp_id>\d+)/$',
        views.xp_capture,
        name='xp_capture'
    ),
    dcu.url(
        r'^xp/new/$',
        views.xp_new,
        name='xp_new'
    ),

    dcu.url(
        r'^cjt/$',
        views.CaptureJobTemplateIndex.as_view(),
        name='cjt_index',
    ),
    dcu.url(
        r'^cjt/new/$',
        views.cjt_new,
        name='cjt_new'
    ),
    dcu.url(
        r'^cjt/(?P<pk>\d+)/$',
        views.CaptureJobTemplateUpdate.as_view(),
        name='cjt_detail'
    ),
    dcu.url(
        r'^cjt/(?P<pk>\d+)/delete/$',
        views.CaptureJobTemplateDelete.as_view(),
        name='cjt_delete'
    ),

    dcu.url(
        r'^sp/$',
        views.SpeciesIndex.as_view(),
        name='sp_index',
    ),
    dcu.url(
        r'^sp/new/$',
        views.sp_new,
        name='sp_new'
    ),
    dcu.url(
        r'^sp/(?P<pk>\d+)/$',
        views.SpeciesUpdate.as_view(),
        name='sp_detail'
    ),
    dcu.url(
        r'^sp/(?P<pk>\d+)/delete/$',
        views.SpeciesDelete.as_view(),
        name='sp_delete'
    ),

    dcu.url(
        r'^cj/(?P<xp_id>\d+)/(?P<cjt_id>\d+)/run/$',
        views.run_capturejob,
        name='run_capturejob'
    ),
    dcu.url(
        r'^cj/abort/$',
        views.abort_capturejob,
        name='abort_capturejob'
    ),

    dcu.url(
        r'^telemetry/$',
        views.receive_telemetry,
        name='receive_telemetry'
    ),

    dcu.url(
        r'^cq/$',
        views.cq_interface,
        name='cq_interface'
    ),
)


