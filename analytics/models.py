from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    course = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=100)
    semester = models.IntegerField()
    roll_no = models.CharField(max_length=50, null=True, blank=True)
    admission_year = models.CharField(max_length=4, null=True, blank=True)
    target_cgpa = models.FloatField(null=True, blank=True, default=8.5)
    current_cgpa = models.FloatField(null=True, blank=True, default=7.24)

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()

    def __str__(self):
        return f"{self.name} ({self.student_id})"

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    credits = models.IntegerField()
    semester = models.IntegerField()

    def __str__(self):
        return f"{self.name} ({self.code})"

class ResultRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    internal_marks = models.FloatField(default=0.0)
    external_marks = models.FloatField(default=0.0)
    attendance_percentage = models.FloatField(default=0.0)
    assignment_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)
    pass_fail_status = models.CharField(max_length=10, choices=[('PASS', 'Pass'), ('FAIL', 'Fail')])

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student.name} - {self.subject.name}: {self.final_score}"

class EmotionalProfile(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='emotional_profiles')
    stress_level = models.IntegerField(help_text="Scale 1-10")
    sleep_hours = models.FloatField()
    study_hours = models.FloatField()
    motivation_score = models.IntegerField(help_text="Scale 1-10")
    burnout_indicator = models.BooleanField(default=False)
    date_logged = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Profile for {self.student.name} on {self.date_logged}"


class WellnessChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    MOOD_LABELS = [
        ('calm', 'Calm'),
        ('focused', 'Focused'),
        ('stressed', 'Stressed'),
        ('anxious', 'Anxious'),
        ('sad', 'Sad'),
        ('overwhelmed', 'Overwhelmed'),
        ('hopeful', 'Hopeful'),
    ]
    student_id = models.CharField(max_length=50, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    # Sentiment tag — populated only on 'user' messages by the AI reply call
    mood_score = models.FloatField(
        null=True, blank=True,
        help_text="Sentiment score from -1.0 (very negative) to +1.0 (very positive)"
    )
    mood_label = models.CharField(
        max_length=20, blank=True, default='',
        choices=MOOD_LABELS,
        help_text="Detected mood category for this user message"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['student_id', 'created_at'])]

    def __str__(self):
        tag = f' [{self.mood_label}]' if self.mood_label else ''
        return f"{self.student_id} [{self.role}]{tag} {self.content[:40]}"
