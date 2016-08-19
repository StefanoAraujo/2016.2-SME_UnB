from django.conf.urls import url

from . import views

app_name = 'data_reader'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<transductor_id>[0-9]+)/$', views.detail, name='detail'),
    url(r'^new$', views.new, name='new'),
    url(r'^(?P<pk>[0-9]+)/edit/$', views.edit, name='edit'),
    url(r'^(?P<pk>[0-9]+)/delete/$', views.delete, name='delete'),
]