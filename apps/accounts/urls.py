from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/', views.KalroLoginView.as_view(), name='login'),
    path('logout/', views.KalroLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),

    # Password reset
    path('password-reset/', views.KalroPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.KalroPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         views.KalroPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/',
         views.KalroPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Password change
    path('password-change/', views.password_change_view, name='password_change'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),

    # User management (KALRO staff only)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserAdminUpdateView.as_view(), name='user_admin_update'),
    path('users/<int:pk>/verify/', views.UserVerifyView.as_view(), name='user_verify'),
    path('users/<int:pk>/unverify/', views.UserUnverifyView.as_view(), name='user_unverify'),

    # Role router (optional, useful as a redirect target)
    path('me/', views.role_router_view, name='role_router'),
]