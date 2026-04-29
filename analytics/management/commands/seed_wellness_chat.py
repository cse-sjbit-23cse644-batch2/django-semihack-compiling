import json
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import WellnessChatMessage

class Command(BaseCommand):
    help = "Seed the database with realistic demo wellness chat messages"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Clear existing messages before seeding")

    def handle(self, *args, **options):
        sid = "2021CS042"  # Akanksha's ID from views.py DEFAULT_STUDENT
        
        if options["reset"]:
            WellnessChatMessage.objects.filter(student_id=sid).delete()
            self.stdout.write(self.style.SUCCESS(f"Cleared existing messages for {sid}"))

        # Realistic 5-turn history sitting over the last 6 days
        # We save messages in pairs (User then AI)
        now = timezone.now()
        
        history = [
            {
                "days_ago": 6,
                "user": "I've been staying up till 3am every night just to finish my assignments. I'm exhausted but I can't stop.",
                "ai": "I hear you — staying up till 3am is a heavy load to carry. This usually stems from 'revenge bedtime procrastination' where you scroll or work late to feel in control of your night. Try this: (1) Set a hard stop at 11:30 PM, (2) leave your phone in another room, and (3) read a physical book for 10 mins before bed. You need your rest to stay sharp.",
                "mood": "stressed", "score": -0.45
            },
            {
                "days_ago": 5,
                "user": "The new schedule is actually working! I slept 7 hours last night and felt so much better today.",
                "ai": "That's fantastic! Getting 7 hours of sleep is a massive win for your cognitive recovery. The underlying cause of your better mood is the stabilized circadian rhythm. Try this: (1) Keep this sleep window consistent for 3 more days, (2) try a short morning walk, and (3) reward yourself with a favorite snack for sticking to the plan. Momentum is on your side!",
                "mood": "hopeful", "score": 0.55
            },
            {
                "days_ago": 3,
                "user": "I have my OS lab viva in 2 days and I'm starting to panic. I feel like I've forgotten everything about deadlocks.",
                "ai": "It's completely natural to feel anxious before a technical viva. This 'memory blank' is usually just your fight-or-flight response taking over. Try this: (1) Review only the top 5 deadlock questions today, (2) explain a concept to a friend or even a rubber duck, and (3) take deep breaths when you feel the panic rising. You know more than you think.",
                "mood": "anxious", "score": -0.60
            },
            {
                "days_ago": 2,
                "user": "I got 14/20 in my OS viva! The deadlock question was exactly what we discussed. Feeling so relieved.",
                "ai": "Congratulations! 14/20 is a solid score and you should be proud of how you handled the pressure. This success confirms that targeted revision works better than panic-studying. Try this: (1) Note down what went well today, (2) take the evening off to celebrate, and (3) apply this same 'targeted review' to your next subject. Great job!",
                "mood": "calm", "score": 0.70
            },
            {
                "days_ago": 0,
                "user": "I have three assignments due this Friday and my parents keep calling me about home stuff. I feel completely overwhelmed.",
                "ai": "I understand — when academic deadlines and family expectations collide, it feels like there's no room to breathe. This overwhelm is a signal that your boundaries are being stretched too thin. Try this: (1) List the 3 assignments by priority, (2) politely tell your parents you'll call them for a longer chat on Saturday, and (3) focus on just the first 15 mins of work. One step at a time.",
                "mood": "overwhelmed", "score": -0.80
            }
        ]

        for entry in history:
            ts = now - timedelta(days=entry["days_ago"])
            # Create user message
            WellnessChatMessage.objects.create(
                student_id=sid, role="user", content=entry["user"],
                mood_label=entry["mood"], mood_score=entry["score"],
                created_at=ts
            )
            # Create AI message
            # We add a few seconds to ensure correct ordering
            WellnessChatMessage.objects.create(
                student_id=sid, role="assistant", content=entry["ai"],
                created_at=ts + timedelta(seconds=10)
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded 5 turns for {sid}"))
