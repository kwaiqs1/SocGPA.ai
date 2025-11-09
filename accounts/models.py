from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school_admin', 'School Admin'),
    ]

    school_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_verified_by_school = models.BooleanField(default=False)

    soc_coins = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.school_name})"
