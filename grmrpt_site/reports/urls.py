from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from reports import views

urlpatterns = [
    path('reports/', views.ReportList.as_view(), name='report-list'),
    path('reports/<int:pk>/', views.ReportDetail.as_view(), name='report-detail'),
    path('runs/', views.RunList.as_view(), name='run-list'),
    path('runs/<int:pk>/', views.RunDetail.as_view(), name='run-detail'),
    path('resorts/', views.ResortList.as_view(), name='resort-list'),
    path('resorts/<int:pk>', views.ResortDetail.as_view(), name='resort-detail')
]

urlpatterns = format_suffix_patterns(urlpatterns)
