# feedback/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.db.models import Q, Count  # Добавлен импорт Q
from .models import Feedback
from .serializers import FeedbackCreateSerializer, FeedbackListSerializer
import logging
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from django.http import Http404, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes

# Настройка логирования
logger = logging.getLogger(__name__)


class FeedbackRateThrottle(AnonRateThrottle):
    """Кастомный throttling для обратной связи"""
    scope = 'feedback'
    rate = '5/hour'  # 5 запросов в час для анонимных пользователей


class AuthenticatedFeedbackRateThrottle(UserRateThrottle):
    """Throttling для авторизованных пользователей"""
    scope = 'feedback_auth'
    rate = '10/hour'  # 10 запросов в час для авторизованных


@method_decorator([csrf_protect, never_cache], name='dispatch')
class FeedbackCreateView(generics.CreateAPIView):
    """
    Создание новой заявки обратной связи
    Защищено от CSRF, имеет rate limiting и логирование
    """
    serializer_class = FeedbackCreateSerializer
    throttle_classes = [FeedbackRateThrottle, AuthenticatedFeedbackRateThrottle]
    permission_classes = [permissions.AllowAny]  # Доступно всем для обратной связи
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def create(self, request, *args, **kwargs):
        """Переопределяем создание для добавления безопасности"""
        
        # Логирование попытки создания
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        logger.info(f"Feedback creation attempt from IP: {client_ip}, User-Agent: {user_agent}")
        
        # Проверка на блокированные IP (если есть система блокировки)
        blocked_ips = getattr(settings, 'BLOCKED_IPS', [])
        if client_ip in blocked_ips:
            logger.warning(f"Blocked IP {client_ip} attempted to create feedback")
            return Response(
                {'error': 'Доступ запрещен'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.warning(f"Invalid feedback data from IP {client_ip}: {str(e)}")
            return Response(
                {'errors': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сохранение с дополнительными данными безопасности
        feedback = serializer.save(
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"Feedback created successfully: ID {feedback.id}, IP: {client_ip}")
        
        return Response(
            {
                'message': 'Ваше сообщение успешно отправлено!',
                'id': feedback.id,
                'status': 'success'
            }, 
            status=status.HTTP_201_CREATED
        )
    
    def handle_exception(self, exc):
        """Обработка исключений"""
        client_ip = self.get_client_ip(self.request)
        logger.error(f"Error in feedback creation from IP {client_ip}: {str(exc)}")
        
        if hasattr(exc, 'status_code') and exc.status_code == 429:
            return Response(
                {'error': 'Слишком много запросов. Попробуйте позже.'}, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        return super().handle_exception(exc)


class FeedbackListView(generics.ListAPIView):
    """
    Список заявок обратной связи (только для администраторов)
    """
    serializer_class = FeedbackListSerializer
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        """Фильтрация и поиск"""
        queryset = Feedback.objects.all()
        
        # Фильтрация по статусу
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтрация по актору
        actor_filter = self.request.query_params.get('actor', None)
        if actor_filter:
            queryset = queryset.filter(actor=actor_filter)
        
        # Поиск по email или имени
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | 
                Q(name_person__icontains=search) |
                Q(theme__icontains=search)
            )
        
        return queryset.order_by('-created_at')


class FeedbackDetailView(generics.RetrieveUpdateAPIView):
    """
    Детальный просмотр и обновление заявки (только для администраторов)
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackListSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        """Безопасное получение объекта"""
        try:
            return super().get_object()
        except:
            logger.warning(f"Attempt to access non-existent feedback: {self.kwargs.get('pk')}")
            raise Http404("Заявка не найдена")
    
    def update(self, request, *args, **kwargs):
        """Обновление только статуса"""
        instance = self.get_object()
        
        # Разрешаем обновлять только статус
        allowed_fields = {'status'}
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        if 'status' in update_data:
            valid_statuses = [choice[0] for choice in Feedback.STATUS_CHOICES]
            if update_data['status'] not in valid_statuses:
                return Response(
                    {'error': 'Неверный статус'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        logger.info(f"Feedback {instance.id} updated by admin")
        
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def feedback_statistics(request):
    """Статистика по заявкам обратной связи"""
    
    stats = {
        'total': Feedback.objects.count(),
        'by_status': dict(
            Feedback.objects.values('status')
            .annotate(count=Count('status'))
            .values_list('status', 'count')
        ),
        'by_actor': dict(
            Feedback.objects.values('actor')
            .annotate(count=Count('actor'))
            .values_list('actor', 'count')
        ),
        'recent': Feedback.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
    }
    
    return Response(stats)


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Возвращает CSRF токен для использования в AJAX запросах
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'csrf_token': token,  # альтернативное имя для совместимости
        'success': True
    })