from linecache import cache

from django.contrib.auth import authenticate
from django.http import Http404
from django.shortcuts import render
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import permission_classes, api_view, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import CustomUser, Profile
from users.serializers import UserSerializer, CustomLoginSerializer, CustomRefreshSerializer, ProfileSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer


@swagger_auto_schema(
    method='post',
    request_body=CustomLoginSerializer,
    responses={200: 'Success'},
    examples={
        'application/json': {
            'username': 'username1',
            'password': 'random_password123$',
        }
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def post_login(request, *args, **kwargs):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(request, username=email, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response({"access_token": access_token,
                         "refresh_token": refresh_token,
                         "user_role": user.user_role}, status=status.HTTP_200_OK)
    else:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(
    method='post',
    request_body=CustomRefreshSerializer,
    responses={200: 'Success'},
    examples={
        'application/json': {
            'refresh_token': 'fdgdfasd',
        }
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request, *args, **kwargs):
    refresh_token = request.data.get('refresh_token')

    if not refresh_token:
        return Response({"detail": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the refresh token is valid
    try:
        # Parse the provided refresh token
        refresh_token = RefreshToken(refresh_token)
        refresh_token.verify()
    except TokenError as e:
        return Response({"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

    # Get user ID from the refresh token
    user_id = refresh_token.payload.get('user_id')

    try:
        # Get the user object based on the user ID
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        raise Http404("User does not exist")

    # Blacklist the current access and refresh tokens
    blacklist_access_token(refresh_token.access_token)
    blacklist_refresh_token(refresh_token)

    # Generate new tokens for the user
    new_tokens = generate_tokens_for_user(user)

    return Response(new_tokens, status=status.HTTP_200_OK)

def blacklist_access_token(access_token):
    # Blacklist the current access token
    cache_key = f"blacklist_{access_token}"
    cache.set(cache_key, "blacklisted", timeout=access_token.lifetime.total_seconds())

def blacklist_refresh_token(refresh_token):
    # Blacklist the current refresh token
    user_id = refresh_token.payload.get('user_id')
    cache_key = f"blacklist_{user_id}_refresh"
    old_refresh_token = str(refresh_token)
    cache.set(cache_key, old_refresh_token, timeout=refresh_token.lifetime.total_seconds())

def generate_tokens_for_user(user):
    # Generate new tokens for the user
    new_refresh = RefreshToken.for_user(user)
    new_access_token = str(new_refresh.access_token)
    new_refresh_token = str(new_refresh)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer