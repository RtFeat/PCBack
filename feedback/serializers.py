# feedback/serializers.py
from rest_framework import serializers
from .models import Feedback
import re
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
import bleach


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания обратной связи"""
    
    class Meta:
        model = Feedback
        fields = [
            'actor', 'theme', 'email', 'name_company', 
            'name_person', 'message'
        ]
        extra_kwargs = {
            'actor': {'required': True},
            'theme': {'required': True},
            'email': {'required': True},
            'name_person': {'required': True},
            'message': {'required': True},
            'name_company': {'required': False},
        }
    
    def validate_email(self, value):
        """Валидация email"""
        if not value:
            raise serializers.ValidationError("Email обязателен для заполнения")
        
        # Проверка на подозрительные домены
        suspicious_domains = [
            'tempmail.org', '10minutemail.com', 'guerrillamail.com',
            'mailinator.com', 'temp-mail.org'
        ]
        
        domain = value.split('@')[1].lower() if '@' in value else ''
        if domain in suspicious_domains:
            raise serializers.ValidationError("Использование временной почты запрещено")
        
        return value.lower().strip()
    
    def validate_theme(self, value):
        """Валидация темы"""
        if not value or not value.strip():
            raise serializers.ValidationError("Тема не может быть пустой")
        
        # Удаляем HTML теги
        clean_value = strip_tags(value).strip()
        
        if len(clean_value) < 5:
            raise serializers.ValidationError("Тема должна содержать минимум 5 символов")
        
        if len(clean_value) > 200:
            raise serializers.ValidationError("Тема не должна превышать 200 символов")
        
        # Проверка на спам-слова
        spam_words = ['casino', 'viagra', 'free money', 'click here', 'win now']
        if any(word in clean_value.lower() for word in spam_words):
            raise serializers.ValidationError("Сообщение содержит запрещенные слова")
        
        return clean_value
    
    def validate_name_person(self, value):
        """Валидация имени"""
        if not value or not value.strip():
            raise serializers.ValidationError("Имя обязательно для заполнения")
        
        clean_value = strip_tags(value).strip()
        
        if len(clean_value) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа")
        
        if len(clean_value) > 100:
            raise serializers.ValidationError("Имя не должно превышать 100 символов")
        
        # Проверка на допустимые символы (буквы, пробелы, дефисы)
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-\.]+$', clean_value):
            raise serializers.ValidationError("Имя должно содержать только буквы, пробелы и дефисы")
        
        return clean_value
    
    def validate_name_company(self, value):
        """Валидация названия компании"""
        if value:
            clean_value = strip_tags(value).strip()
            
            if len(clean_value) > 150:
                raise serializers.ValidationError("Название компании не должно превышать 150 символов")
            
            return clean_value
        return value
    
    def validate_message(self, value):
        """Валидация сообщения"""
        if not value or not value.strip():
            raise serializers.ValidationError("Сообщение обязательно для заполнения")
        
        # Разрешаем только безопасные HTML теги
        allowed_tags = ['p', 'br', 'strong', 'em', 'u']
        clean_value = bleach.clean(value, tags=allowed_tags, strip=True).strip()
        
        if len(clean_value) < 10:
            raise serializers.ValidationError("Сообщение должно содержать минимум 10 символов")
        
        if len(clean_value) > 2000:
            raise serializers.ValidationError("Сообщение не должно превышать 2000 символов")
        
        # Проверка на спам
        spam_words = ['casino', 'viagra', 'free money', 'click here', 'win now']
        if any(word in clean_value.lower() for word in spam_words):
            raise serializers.ValidationError("Сообщение содержит запрещенные слова")
        
        # Проверка на повторяющиеся символы (признак спама)
        if re.search(r'(.)\1{10,}', clean_value):
            raise serializers.ValidationError("Сообщение содержит слишком много повторяющихся символов")
        
        return clean_value
    
    def validate_actor(self, value):
        """Валидация актора"""
        valid_actors = [choice[0] for choice in Feedback.ACTOR_CHOICES]
        if value not in valid_actors:
            raise serializers.ValidationError("Неверный тип актора")
        return value
    
    def validate(self, attrs):
        """Общая валидация"""
        # Проверка на дублирование (один email не может отправить одинаковые сообщения в течение часа)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_feedback = Feedback.objects.filter(
            email=attrs.get('email'),
            theme=attrs.get('theme'),
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        
        if recent_feedback:
            raise serializers.ValidationError(
                "Вы уже отправляли похожее сообщение в течение последнего часа"
            )
        
        return attrs


class FeedbackListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка обратной связи (только для чтения)"""
    
    actor_display = serializers.CharField(source='get_actor_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'created_at', 'actor', 'actor_display', 
            'theme', 'email', 'name_company', 'name_person', 
            'message', 'status_display'
        ]
        read_only_fields = fields