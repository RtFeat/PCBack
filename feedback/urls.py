from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeedbackCreateView, FeedbackListView, FeedbackDetailView, feedback_statistics, get_csrf_token


app_name = 'feedback'

# REST API URLs
urlpatterns = [
    # API для создания обратной связи
    path('create/', FeedbackCreateView.as_view(), name='create'),
    
    # API для списка (только для администраторов)
    path('list/', FeedbackListView.as_view(), name='list'),
    
    # API для детального просмотра и обновления
    path('<int:pk>/', FeedbackDetailView.as_view(), name='detail'),
    
    # Статистика (для администраторов)
    path('statistics/', feedback_statistics, name='statistics'),

    path('get-csrf-token/', get_csrf_token, name='get_csrf_token'),
]