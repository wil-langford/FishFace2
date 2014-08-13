import django.conf.urls as dcu
import djff.views as views

urlpatterns = dcu.patterns(
    '',
    dcu.url(r'^$', views.index, name='index'),
)