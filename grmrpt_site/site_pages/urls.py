from django.urls import path
from django.contrib.auth.views import LoginView
from rest_framework.urlpatterns import format_suffix_patterns
from django.conf.urls import url

from site_pages import views

urlpatterns = [
    path('signup/', views.create_user, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/alert<slug:alert>', views.profile_view, name='profile-alert'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact_us, name='contact_us'),
    path('deleteme/', views.delete, name='delete'),
    path('', views.index, name='index'),
    path('bmreports/', views.reports, name='reports')
]

urlpatterns = format_suffix_patterns(urlpatterns)
