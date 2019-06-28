from django.conf.urls import url
# from django.contrib import admin
from simhash_service import views
urlpatterns = [
    url(r"status", views.alive),
    url(r'', views.check_sim),
]
