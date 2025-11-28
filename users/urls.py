from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('redirect-after-login/', views.redirect_after_login, name='redirect_after_login'),
    path('social-login-redirect/', views.social_login_redirect, name='social_redirect'),

]


