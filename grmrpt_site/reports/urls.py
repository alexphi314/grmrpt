from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from reports import views

urlpatterns = [
    path('reports/', views.ReportList.as_view()),
    path('reports/<int:pk>/', views.ReportDetail.as_view()),
    path('runs/', views.RunList.as_view()),
    path('runs/<int:pk>/', views.RunDetail.as_view(), name='run-detail'),
    path('resorts/', views.ResortList.as_view()),
    path('resorts/<int:pk>', views.ResortDetail.as_view(), name='resort-detail')
]

urlpatterns = format_suffix_patterns(urlpatterns)
