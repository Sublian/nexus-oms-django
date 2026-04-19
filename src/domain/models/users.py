import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    STAFF = 'STAFF', 'Operador'
    VIEWER = 'VIEWER', 'Solo Lectura'


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser debe tener is_staff=True')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser debe tener is_superuser=True')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,   # null permite superusers sin organización (admin central)
        blank=True,
    )
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.STAFF,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_viewer(self):
        return self.role == UserRole.VIEWER
