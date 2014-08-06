import django.conf.urls as dcu
from djff import views

urlpatterns = dcu.patterns(
    '',
    dcu.url(r'^$', views.IndexView.as_view(), name='index'),
)