from django.db import models
from django.conf import settings


class Achievement(models.Model):
    CATEGORY_CHOICES = [
        ('research', 'Научно-исследовательская деятельность'),
        ('social', 'Социальная и волонтерская активность'),
        ('creative', 'Творческая деятельность'),
        ('sports', 'Спортивные достижения'),
        ('competence', 'Развитие компетенций'),
        ('other', 'Другое'),
    ]

    SCALE_CHOICES = [
        ('school', 'School'),
        ('city', 'City / Region'),
        ('national', 'National'),
        ('international', 'International'),
    ]

    ROLE_CHOICES = [
        ('participant', 'Participant'),
        ('winner', 'Winner / Prize'),
        ('organizer', 'Organizer'),
        ('leader', 'Leader / Founder'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements'
    )

    title = models.CharField(max_length=255)


    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='other'
    )


    subcategory = models.CharField(
        max_length=120,
        blank=True
    )

    description = models.TextField(blank=True)

    scale = models.CharField(
        max_length=30,
        choices=SCALE_CHOICES,
        default='school'
    )
    role_type = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='participant'
    )

    duration_months = models.PositiveIntegerField(default=0)

    proof_file = models.FileField(
        upload_to='proofs/',
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    ai_raw_response = models.JSONField(blank=True, null=True)
    total_points = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user}"

    def calculate_points(self):
        base_by_category = {
            'research': 9,
            'social': 7,
            'creative': 6,
            'sports': 6,
            'competence': 8,
            'other': 4,
        }

        scale_mult = {
            'school': 1.0,
            'city': 1.1,
            'national': 1.3,
            'international': 1.6,
        }

        role_mult = {
            'participant': 1.0,
            'winner': 1.4,
            'organizer': 1.3,
            'leader': 1.6,
        }


        duration_mult = 1.0 + min(self.duration_months, 12) / 24

        verified_mult = 1.0
        if self.status == 'approved':
            verified_mult = 1.2
        elif self.status == 'rejected':
            verified_mult = 0.0

        base = base_by_category.get(self.category, 4)
        points = base * scale_mult.get(self.scale, 1.0) * role_mult.get(self.role_type, 1.0)
        points *= duration_mult * verified_mult

        return round(points, 2)


class ShopItem(models.Model):
    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField()  # SocCoins
    discount_info = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.price} SocCoins)"


class UserPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user} -> {self.item}"


class Quest(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    reward_coins = models.PositiveIntegerField(default=100)

    def __str__(self):
        return self.title


class QuestCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'quest')

    def __str__(self):
        return f"{self.user} completed {self.quest}"


class Event(models.Model):
    title = models.CharField(max_length=255)
    organizer = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    date = models.CharField(max_length=50)
    location = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title

