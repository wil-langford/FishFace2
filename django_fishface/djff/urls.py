import django.conf.urls as dcu
import djff.views as views
urlpatterns = dcu.patterns(
    '',
    dcu.url(
        r'^upload_imagery/$',
        views.receive_image,
        name='receive_image'
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
        r'^cj/abort_job/$',
        views.abort_running_job,
        name='abort_running_job'
    ),

    dcu.url(
        r'^telemetry/$',
        views.receive_telemetry,
        name='receive_telemetry'
    ),

    dcu.url(
      r'^telemetry_proxy/$',
      views.telemetry_proxy,
      name='telemetry_proxy'
    ),

    dcu.url(
        r'^cq/$',
        views.cq_interface,
        name='cq_interface'
    ),

    dcu.url(
        r'^cq_builder/$',
        views.cq_builder,
        name='cq_builder'
    ),

    dcu.url(
        r'^cq_saver/$',
        views.cq_saver,
        name='cq_saver'
    ),

    dcu.url(
        r'^tag/$',
        views.tagging_interface,
        name='tagging_interface'
    ),

    dcu.url(
        r'^tag_submit/$',
        views.tag_submit,
        name='tag_submit'
    ),

    dcu.url(
        r'^verification/$',
        views.verification_interface,
        name='verification_interface'
    ),

    dcu.url(
        r'^verification_submit/$',
        views.verification_submit,
        name='verification_submit'
    ),

    dcu.url(
        r'^cjr/new_for_raspi/$',
        views.cjr_new_for_raspi,
        name='cjr_new_for_raspi'
    ),

    dcu.url(
        r'^stats/$',
        views.stats,
        name='stats'
    ),

    dcu.url(
        r'^verification_image/manual_tag_(?P<tag_id>\d+).jpg',
        views.manual_tag_verification_image,
        name='manual_tag_verification_image'
    ),
)


