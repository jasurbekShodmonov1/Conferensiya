from django.urls import path, include
from rest_framework import routers

from .views import UserViewSet,ProfileViewSet

router = routers.DefaultRouter()
router.register(r'register', UserViewSet, basename='register')
router.register(r'profile', ProfileViewSet, basename='profile')


urlpatterns = [
    path('', include(router.urls)),
    ]
