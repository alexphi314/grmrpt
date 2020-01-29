from django.urls import path
from django.conf.urls import include
from django.contrib.auth.views import LoginView, LogoutView
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.authtoken.views import obtain_auth_token

from reports import views

urlpatterns = [
    path('reports/', views.ReportList.as_view(), name='report-list'),
    path('reports/<int:pk>/', views.ReportDetail.as_view(), name='report-detail'),
    path('runs/', views.RunList.as_view(), name='run-list'),
    path('runs/<int:pk>/', views.RunDetail.as_view(), name='run-detail'),
    path('resorts/', views.ResortList.as_view(), name='resort-list'),
    path('resorts/<int:pk>/', views.ResortDetail.as_view(), name='resort-detail'),
    path('bmreports/', views.BMReportList.as_view(), name='bmreport-list'),
    path('bmreports/<int:pk>/', views.BMReportDetail.as_view(), name='bmreport-detail'),
    path('api/', views.api_root, name='api-index'),
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('users/', views.UserList.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetail.as_view(), name='user-detail'),
    path('bmgusers/', views.BMGUserList.as_view(), name='bmguser-list'),
    path('bmgusers/<int:pk>/', views.BMGUserDetail.as_view(), name='bmguser-detail'),
    path('notifications/', views.NotificationList.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', views.NotificationDetail.as_view(), name='notification-detail'),
    path('signup/', views.create_user, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact_us, name='contact_us'),
    path('', views.index, name='index')
]

urlpatterns = format_suffix_patterns(urlpatterns)
