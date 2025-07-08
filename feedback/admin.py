# feedback/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.http import HttpResponse
import csv
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Администрирование заявок обратной связи"""
    
    # Отображение в списке
    list_display = [
        'id',
        'colored_status',
        'actor_display',
        'name_person',
        'email',
        'theme_short',
        'message_short',
        'created_at_display',
        'days_since_creation',
    ]
    
    # Фильтры в боковой панели
    list_filter = [
        'status',
        'actor',
        ('created_at', admin.DateFieldListFilter),
        'updated_at',
    ]
    
    # Поля для поиска
    search_fields = [
        'email',
        'name_person',
        'name_company',
        'theme',
        'message',
        'ip_address',
    ]
    
    # Поля только для чтения
    readonly_fields = [
        'created_at',
        'updated_at',
        'ip_address',
        'user_agent',
        'id',
        'colored_status_detail',
        'days_since_creation',
    ]
    
    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'id',
                'colored_status_detail',
                'status',
                'actor',
                'theme',
            )
        }),
        ('Контактные данные', {
            'fields': (
                'name_person',
                'name_company',
                'email',
            )
        }),
        ('Сообщение', {
            'fields': (
                'message',
            )
        }),
        ('Системная информация', {
            'fields': (
                'created_at',
                'updated_at',
                'days_since_creation',
                'ip_address',
                'user_agent',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Сортировка по умолчанию
    ordering = ['-created_at']
    
    # Количество записей на странице
    list_per_page = 25
    
    # Пагинация в верхней части
    list_select_related = True
    
    # Действия для выбранных объектов
    actions = [
        'mark_as_completed',
        'mark_as_rejected', 
        'mark_as_new',
        'export_as_csv',
    ]
    
    def colored_status(self, obj):
        """Цветное отображение статуса в списке"""
        color = obj.get_status_color()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Статус'
    colored_status.admin_order_field = 'status'
    
    def colored_status_detail(self, obj):
        """Цветное отображение статуса в детальной форме"""
        color = obj.get_status_color()
        return format_html(
            '<div style="background-color: {}; color: white; padding: 10px; '
            'border-radius: 5px; text-align: center; font-weight: bold; '
            'font-size: 14px; max-width: 200px;">{}</div>',
            color,
            obj.get_status_display()
        )
    colored_status_detail.short_description = 'Текущий статус'
    
    def actor_display(self, obj):
        """Отображение роли с иконкой"""
        icons = {
            'advertiser': '📈',
            'author': '✍️',
            'question': '❓',
        }
        icon = icons.get(obj.actor, '👤')
        return f"{icon} {obj.get_actor_display()}"
    actor_display.short_description = 'Роль'
    actor_display.admin_order_field = 'actor'
    
    def theme_short(self, obj):
        """Короткое отображение темы"""
        if len(obj.theme) > 40:
            return f"{obj.theme[:40]}..."
        return obj.theme
    theme_short.short_description = 'Тема'
    theme_short.admin_order_field = 'theme'
    
    def message_short(self, obj):
        """Короткое отображение сообщения"""
        # Убираем HTML теги для отображения
        import re
        clean_message = re.sub('<.*?>', '', obj.message)
        if len(clean_message) > 50:
            return f"{clean_message[:50]}..."
        return clean_message
    message_short.short_description = 'Сообщение'
    
    def created_at_display(self, obj):
        """Красивое отображение даты создания"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_display.short_description = 'Дата создания'
    created_at_display.admin_order_field = 'created_at'
    
    def days_since_creation(self, obj):
        """Количество дней с момента создания"""
        delta = timezone.now() - obj.created_at
        days = delta.days
        
        if days == 0:
            return "Сегодня"
        elif days == 1:
            return "1 день назад"
        elif days < 7:
            return f"{days} дней назад"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} недель назад"
        else:
            months = days // 30
            return f"{months} месяцев назад"
    days_since_creation.short_description = 'Давность'
    
    # Действия для массового изменения статусов
    def mark_as_completed(self, request, queryset):
        """Отметить как выполненное"""
        count = queryset.update(status='completed')
        self.message_user(
            request, 
            f'{count} заявок отмечено как выполненные.'
        )
    mark_as_completed.short_description = "Отметить как выполненные"
    
    def mark_as_rejected(self, request, queryset):
        """Отметить как отклоненное"""
        count = queryset.update(status='rejected')
        self.message_user(
            request, 
            f'{count} заявок отмечено как отклоненные.'
        )
    mark_as_rejected.short_description = "Отметить как отклоненные"
    
    def mark_as_new(self, request, queryset):
        """Отметить как новое"""
        count = queryset.update(status='new')
        self.message_user(
            request, 
            f'{count} заявок отмечено как новые.'
        )
    mark_as_new.short_description = "Отметить как новые"
    
    def export_as_csv(self, request, queryset):
        """Экспорт выбранных заявок в CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="feedback_export.csv"'
        
        # Добавляем BOM для корректного отображения в Excel
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Заголовки
        writer.writerow([
            'ID',
            'Дата создания',
            'Роль',
            'Статус',
            'Имя',
            'Компания',
            'Email',
            'Тема',
            'Сообщение',
            'IP адрес',
        ])
        
        # Данные
        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.created_at.strftime('%d.%m.%Y %H:%M'),
                obj.get_actor_display(),
                obj.get_status_display(),
                obj.name_person,
                obj.name_company or '',
                obj.email,
                obj.theme,
                obj.message.replace('\n', ' ').replace('\r', ''),
                obj.ip_address or '',
            ])
        
        return response
    export_as_csv.short_description = "Экспортировать в CSV"
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related()
    
    def has_delete_permission(self, request, obj=None):
        """Ограничение на удаление - только для суперпользователей"""
        return request.user.is_superuser
    
    def get_readonly_fields(self, request, obj=None):
        """Динамические readonly поля"""
        readonly = list(self.readonly_fields)
        
        # Обычные администраторы могут изменять только статус
        if not request.user.is_superuser and obj:
            readonly.extend([
                'actor', 'theme', 'email', 'name_company', 
                'name_person', 'message'
            ])
        
        return readonly


# Дополнительный класс для отображения статистики в админке
class FeedbackStatsMixin:
    """Миксин для добавления статистики"""
    
    def changelist_view(self, request, extra_context=None):
        """Добавление статистики в список"""
        extra_context = extra_context or {}
        
        # Общая статистика
        total_count = Feedback.objects.count()
        new_count = Feedback.objects.filter(status='new').count()
        completed_count = Feedback.objects.filter(status='completed').count()
        rejected_count = Feedback.objects.filter(status='rejected').count()
        
        # Статистика за последние дни
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_count = Feedback.objects.filter(
            created_at__date=today
        ).count()
        
        week_count = Feedback.objects.filter(
            created_at__date__gte=week_ago
        ).count()
        
        month_count = Feedback.objects.filter(
            created_at__date__gte=month_ago
        ).count()
        
        extra_context.update({
            'feedback_stats': {
                'total': total_count,
                'new': new_count,
                'completed': completed_count,
                'rejected': rejected_count,
                'today': today_count,
                'week': week_count,
                'month': month_count,
            }
        })
        
        return super().changelist_view(request, extra_context)


# Применяем миксин к нашему админ-классу
FeedbackAdmin.__bases__ = (FeedbackStatsMixin,) + FeedbackAdmin.__bases__