from django.urls import path
from django.contrib.auth import views as auth_views
from rest_framework.urlpatterns import format_suffix_patterns
from django.conf.urls import url

from site_pages import views

urlpatterns = [
    path('signup/', views.create_user, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/alert<slug:alert>', views.profile_view, name='profile-alert'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='password_change.html'),
         name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'),
         name='password_change_done'),
    path('password_reset', auth_views.PasswordResetView.as_view(template_name='password_reset.html'),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
         name='password_reset_complete'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact_us, name='contact_us'),
    path('deleteme/', views.delete, name='delete'),
    path('', views.index, name='index'),
    path('bmreports/', views.reports, name='reports'),
    path('runs/<int:run_id>', views.run_stats, name='run-stats'),
    path('images/runs/<int:run_id>', views.run_stats_img, name='run-stats-plot')
]

urlpatterns = format_suffix_patterns(urlpatterns)
