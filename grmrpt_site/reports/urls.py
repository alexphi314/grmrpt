from django.urls import path
from django.conf.urls import include
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
    path('hdreports/', views.HDReportList.as_view(), name='hdreport-list'),
    path('hdreports/<int:pk>/', views.HDReportDetail.as_view(), name='hdreport-detail'),
    path('', views.api_root),
    path('api-auth/', include('rest_framework.urls')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
