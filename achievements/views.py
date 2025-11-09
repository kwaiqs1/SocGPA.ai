from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.utils import timezone
from accounts.models import User
from .forms import AchievementForm
from .models import (
    Achievement,
    ShopItem,
    UserPurchase,
    Quest,
    QuestCompletion,
    Event,
)
from .utils import analyze_achievement_with_ai

from collections import defaultdict
from datetime import timedelta
import math




def compute_social_gpa_for_user(user):

    qs = user.achievements.filter(status='approved').order_by('created_at')
    if not qs.exists():
        return 0.0, 0.0

    achievements = list(qs)


    B = 10.0


    W_CAT = {
        'research': 1.5,
        'social': 1.4,
        'creative': 1.1,
        'sports': 1.1,
        'competence': 0.9,
        'other': 0.7,
    }

    W_SCALE = {
        'school': 1.0,
        'city': 1.3,
        'national': 2.0,
        'international': 3.0,
    }

    W_ROLE = {
        'participant': 0.7,
        'winner': 1.6,
        'organizer': 1.6,
        'leader': 2.0,
    }

    def w_duration(months):

        try:
            m = float(months or 0)
        except (TypeError, ValueError):
            m = 0.0

        if m <= 0:
            return 0.7
        if m <= 1:
            return 1.0
        if m <= 4:
            return 1.3
        if m <= 6:
            return 1.7
        return 2.0


    now = timezone.now()
    year_ago = now - timedelta(days=365)


    groups = defaultdict(list)

    for idx, ach in enumerate(achievements):
        if ach.created_at and ach.created_at >= year_ago:
            title = (ach.title or "").lower()

            norm = ''.join(ch if (ch.isalnum() or ch.isspace()) else ' ' for ch in title)
            norm = ' '.join(norm.split()[:6])
            key = (ach.category or 'other', ach.scale or 'school', norm)
            groups[key].append(idx)



    f_repeat = [1.0] * len(achievements)

    for key, idxs in groups.items():
        if not idxs:
            continue

        for j, pos in enumerate(sorted(idxs), start=1):
            f_repeat[pos] = 1.0 / math.sqrt(j)


    raw_score = 0.0

    for idx, ach in enumerate(achievements):
        cat = ach.category or 'other'
        scale = ach.scale or 'school'
        role = ach.role_type or 'participant'

        wc = W_CAT.get(cat, 0.7)
        ws = W_SCALE.get(scale, 1.0)
        wr = W_ROLE.get(role, 0.7)
        wd = w_duration(ach.duration_months)
        fr = f_repeat[idx]

        score_i = B * wc * ws * wr * wd * fr
        raw_score += score_i


    social_gpa = 10.0 * math.log10(1.0 + raw_score)
    social_gpa = round(social_gpa, 2)

    return raw_score, social_gpa



def ensure_default_shop_items():
    if ShopItem.objects.exists():
        return
    ShopItem.objects.bulk_create([
        ShopItem(
            name="30% off SAT Prep Course",
            provider="SmartEsPrep",
            description="Intensive SAT course with live instructors.",
            price=2000,
            discount_info="30% discount code emailed after purchase."
        ),
        ShopItem(
            name="25% off IELTS Mastery",
            provider="Master Education",
            description="Full IELTS preparation program.",
            price=1800,
            discount_info="25% discount on any IELTS course."
        ),
        ShopItem(
            name="50% off Coding Bootcamp",
            provider="CodeBridge",
            description="Python & Web dev bootcamp for teens.",
            price=2500,
            discount_info="50% off on selected cohorts."
        ),
        ShopItem(
            name="20% off Debate Academy",
            provider="OratoryLab",
            description="Public speaking & MUN training.",
            price=1500,
            discount_info="20% discount voucher."
        ),
        ShopItem(
            name="35% off Data Science Basics",
            provider="EduFuture",
            description="Beginner-friendly DS & ML course.",
            price=2200,
            discount_info="35% off full course."
        ),
    ])


def ensure_default_quests():
    if Quest.objects.exists():
        return
    Quest.objects.bulk_create([
        Quest(
            title="Join 2 Debate Tournaments",
            description="Upload 2 verified debate achievements.",
            reward_coins=500
        ),
        Quest(
            title="Organize a School Event",
            description="Upload a leadership/organizer certificate.",
            reward_coins=700
        ),
        Quest(
            title="Complete 10h Volunteering",
            description="Upload volunteering certificate with 10+ hours.",
            reward_coins=400
        ),
    ])


def ensure_default_events():
    if Event.objects.exists():
        return
    Event.objects.bulk_create([
        Event(
            title="National STEM Olympiad",
            organizer="Ministry of Education",
            category="Competition",
            date="March 2026",
            location="Astana, Kazakhstan",
            link="#"
        ),
        Event(
            title="Youth Social Impact Hackathon",
            organizer="FutureLab",
            category="Hackathon",
            date="April 2026",
            location="Online",
            link="#"
        ),
        Event(
            title="Environmental Volunteering Week",
            organizer="Green Earth NGO",
            category="Volunteering",
            date="May 2026",
            location="Your city",
            link="#"
        ),
        Event(
            title="Entrepreneurship Case Championship",
            organizer="BizUp Academy",
            category="Competition",
            date="June 2026",
            location="Almaty, Kazakhstan",
            link="#"
        ),
    ])



@login_required
def dashboard_view(request):
    user = request.user
    achievements = user.achievements.filter(status='approved').order_by('-created_at')


    total_points = achievements.aggregate(total=Sum('total_points'))['total'] or 0


    raw_social_score, social_gpa = compute_social_gpa_for_user(user)


    max_display_gpa = 40.0
    progress_percent = int(min((social_gpa / max_display_gpa) * 100, 100))

    recommendations = []
    for a in achievements:
        if a.ai_raw_response and a.ai_raw_response.get('missing_recommendations'):
            recommendations.extend(a.ai_raw_response['missing_recommendations'])
    recommendations = list(dict.fromkeys(recommendations))[:3]

    context = {
        'user': user,
        'achievements': achievements[:5],
        'total_points': total_points,
        'social_gpa': social_gpa,
        'raw_social_score': round(raw_social_score, 1),
        'progress_percent': progress_percent,
        'recommendations': recommendations,
    }
    return render(request, 'achievements/dashboard.html', context)


@login_required
def add_achievement_view(request):
    if request.method == 'POST':
        form = AchievementForm(request.POST, request.FILES)
        if form.is_valid():
            achievement = form.save(commit=False)
            achievement.user = request.user
            achievement.status = 'pending'
            achievement.save()

            file_path = achievement.proof_file.path if achievement.proof_file else None
            existing = request.user.achievements.filter(status='approved').exclude(id=achievement.id)
            by_category = {}
            for a in existing:
                key = a.category or "other"
                by_category[key] = by_category.get(key, 0) + 1
            profile_summary = {
                "total": existing.count(),
                "by_category": by_category,
            }

            ai_result = analyze_achievement_with_ai(
                user_full_name=request.user.get_full_name() or request.user.username,
                title=achievement.title,
                category=achievement.category,
                description=achievement.description,
                file_path=file_path,
                profile_summary=profile_summary,
            )


            achievement.category = ai_result.get('category', achievement.category)
            achievement.scale = ai_result.get('scale', achievement.scale)
            achievement.role_type = ai_result.get('role_type', achievement.role_type)
            achievement.duration_months = ai_result.get('duration_months', achievement.duration_months)
            achievement.ai_raw_response = ai_result


            achievement.status = 'approved'

            achievement.total_points = achievement.calculate_points()
            achievement.save()


            total_score = ai_result.get('total_score', achievement.total_points)
            coins_earned = int(max(total_score, 10))
            request.user.soc_coins += coins_earned
            request.user.save()

            return render(request, 'achievements/analysis_result.html', {
                'achievement': achievement,
                'ai_result': ai_result,
                'coins_earned': coins_earned,
            })
    else:
        form = AchievementForm()

    return render(request, 'achievements/add_achievement.html', {'form': form})



@login_required
def leaderboard_view(request):
    users = User.objects.annotate(
        total_points=Sum('achievements__total_points')
    ).order_by('-total_points', '-soc_coins')[:100]

    return render(request, 'achievements/leaderboard.html', {'users': users})



@login_required
def profile_view(request, user_id=None):
    if user_id:
        profile_user = get_object_or_404(User, id=user_id)
    else:
        profile_user = request.user

    achievements = profile_user.achievements.filter(status='approved')
    total_points = achievements.aggregate(total=Sum('total_points'))['total'] or 0

    raw_social_score, social_gpa = compute_social_gpa_for_user(profile_user)

    milestones = [
        {"threshold": 50, "reward": "100 SocCoins"},
        {"threshold": 150, "reward": "20% off IELTS course"},
        {"threshold": 300, "reward": "30% off SAT course"},
        {"threshold": 600, "reward": "Mentor session"},
        {"threshold": 1000, "reward": "Premium badge"},
    ]

    return render(request, 'achievements/profile.html', {
        'profile_user': profile_user,
        'achievements': achievements,
        'total_points': total_points,
        'social_gpa': social_gpa,
        'raw_social_score': round(raw_social_score, 1),
        'milestones': milestones,
    })



@login_required
def shop_view(request):
    ensure_default_shop_items()
    items = ShopItem.objects.all()
    purchases = {p.item_id for p in UserPurchase.objects.filter(user=request.user)}

    message = None
    error = None

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(ShopItem, id=item_id)
        if item.id in purchases:
            error = "You already own this reward."
        elif request.user.soc_coins < item.price:
            error = "Not enough SocCoins."
        else:
            UserPurchase.objects.create(user=request.user, item=item)
            request.user.soc_coins -= item.price
            request.user.save()
            purchases.add(item.id)
            message = f"You purchased: {item.name}. {item.discount_info}"

    return render(request, 'achievements/shop.html', {
        'items': items,
        'purchases': purchases,
        'message': message,
        'error': error,
    })



@login_required
def quests_view(request):
    ensure_default_quests()
    quests = Quest.objects.all()
    completed_ids = {
        qc.quest_id for qc in QuestCompletion.objects.filter(user=request.user)
    }

    message = None

    if request.method == 'POST':
        quest_id = request.POST.get('quest_id')
        quest = get_object_or_404(Quest, id=quest_id)
        if quest.id not in completed_ids:
            QuestCompletion.objects.create(user=request.user, quest=quest)
            request.user.soc_coins += quest.reward_coins
            request.user.save()
            completed_ids.add(quest.id)
            message = f"Quest completed! +{quest.reward_coins} SocCoins"

    return render(request, 'achievements/quests.html', {
        'quests': quests,
        'completed_ids': completed_ids,
        'message': message,
    })



@login_required
def search_people_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        parts = query.split()
        q = Q()
        for part in parts:
            q &= (Q(first_name__icontains=part) |
                  Q(last_name__icontains=part) |
                  Q(username__icontains=part))
        results = User.objects.filter(q)[:50]

    return render(request, 'achievements/search_people.html', {
        'query': query,
        'results': results,
    })



@login_required
def extracurriculars_view(request):
    ensure_default_events()
    events = Event.objects.all()
    return render(request, 'achievements/extracurriculars.html', {'events': events})


