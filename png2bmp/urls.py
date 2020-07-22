from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index_v1', views.index_v1, name='index_v1'),
]