# feedback/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator, MinLengthValidator, MaxLengthValidator
import bleach


class Feedback(models.Model):
    """Модель обратной связи"""
    
    ACTOR_CHOICES = [
        ('advertiser', 'Я рекламодатель'),
        ('author', 'Я автор'),
        ('question', 'Я просто спросить'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('completed', 'Выполнено'),
        ('rejected', 'Отклонено'),
    ]
    
    # Автоматически создается Django
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    actor = models.CharField(
        max_length=20,
        choices=ACTOR_CHOICES,
        verbose_name='Роль'
    )
    
    theme = models.CharField(
        max_length=200,
        validators=[
            MinLengthValidator(5, message='Тема должна содержать минимум 5 символов'),
            MaxLengthValidator(200, message='Тема не должна превышать 200 символов')
        ],
        verbose_name='Тема'
    )
    
    email = models.EmailField(
        validators=[EmailValidator()],
        verbose_name='Email'
    )
    
    name_company = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(150)],
        verbose_name='Название компании'
    )
    
    name_person = models.CharField(
        max_length=100,
        validators=[
            MinLengthValidator(2, message='Имя должно содержать минимум 2 символа'),
            MaxLengthValidator(100, message='Имя не должно превышать 100 символов')
        ],
        verbose_name='Имя'
    )
    
    message = models.TextField(
        validators=[
            MinLengthValidator(10, message='Сообщение должно содержать минимум 10 символов'),
            MaxLengthValidator(2000, message='Сообщение не должно превышать 2000 символов')
        ],
        verbose_name='Сообщение'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )
    
    # Поля для безопасности
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP адрес'
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name='User Agent'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Обратная связь'
        verbose_name_plural = 'Обратная связь'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['email']),
            models.Index(fields=['actor']),
        ]
    
    def __str__(self):
        return f"{self.get_actor_display()} - {self.theme[:50]}"
    
    def save(self, *args, **kwargs):
        # Санитизация данных перед сохранением
        if self.theme:
            self.theme = bleach.clean(self.theme, strip=True)
        
        if self.name_person:
            self.name_person = bleach.clean(self.name_person, strip=True)
        
        if self.name_company:
            self.name_company = bleach.clean(self.name_company, strip=True)
        
        if self.message:
            # Разрешаем только безопасные HTML теги
            allowed_tags = ['p', 'br', 'strong', 'em', 'u']
            self.message = bleach.clean(
                self.message, 
                tags=allowed_tags, 
                strip=True
            )
        
        super().save(*args, **kwargs)
    
    def get_status_color(self):
        """Возвращает цвет для статуса в админке"""
        colors = {
            'new': '#FFA500',  # Оранжевый
            'completed': '#28A745',  # Зеленый
            'rejected': '#DC3545',  # Красный
        }
        return colors.get(self.status, '#6C757D')
    
    @property
    def is_new(self):
        return self.status == 'new'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'