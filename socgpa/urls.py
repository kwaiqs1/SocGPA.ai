from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from accounts.views import register_view
from achievements.views import (
    dashboard_view,
    add_achievement_view,
    leaderboard_view,
    profile_view,
    shop_view,
    quests_view,
    search_people_view,
    extracurriculars_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', dashboard_view, name='dashboard'),
    path('add/', add_achievement_view, name='add_achievement'),
    path('leaderboard/', leaderboard_view, name='leaderboard'),
    path('profile/', profile_view, name='my_profile'),
    path('profile/<int:user_id>/', profile_view, name='profile'),
    path('shop/', shop_view, name='shop'),
    path('quests/', quests_view, name='quests'),
    path('search-people/', search_people_view, name='search_people'),
    path('extracurriculars/', extracurriculars_view, name='extracurriculars'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
