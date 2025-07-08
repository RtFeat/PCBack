# feedback/apps.py
from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    """Конфигурация приложения обратной связи"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feedback'
    verbose_name = 'Обратная связь'