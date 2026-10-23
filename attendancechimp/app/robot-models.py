"""
Database models for a course management and QR-based attendance system.

Models
------
InstructorProfile
    Stores the profile of an instructor.

StudentProfile
    Stores the profile of a student.

Course
    Represents a course taught by one instructor, with a meeting schedule.

Enrollment
    Connects students to courses through a many-to-many relationship.
    Uses a composite primary key consisting of student_id and course_id.

Lecture
    Represents an individual lecture or class session belonging to a course.
    Each lecture has a date and a unique QR identifier.

QRCodeUpload
    Records a student's QR-code attendance submission. A submission may
    optionally reference a lecture if the lecture has not yet been identified.

Compatibility
-------------
Requires Django 5.2+ for models.CompositePrimaryKey.
"""

"""
I used ChatGPT.
Prompt: Please generate a Django models.py file that meets the following specification:
InstructorProfile / StudentProfile tables
Course table with at least name, instructor, meeting schedule
Enrollment table: links students to courses (many-to-many)
Lecture table: linked to a course, has a date and a QR identifier
QRCodeUpload table: linked to a student and (optionally) a lecture

Write detailed doc strings, and if applicable, helper functions
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InstructorProfile(models.Model):
    """
    Profile information for an instructor.

    The instructor's primary key is explicitly defined rather than allowing
    Django to generate its default `id` field.

    A one-to-one relationship with the configured user model ensures that
    each user has at most one instructor profile.

    Fields
    ------
    instructor_id:
        Explicit primary key for the instructor profile.
    user:
        User account associated with this instructor.
    display_name:
        Name displayed to students.
    department:
        Optional academic department.
    """

    instructor_id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )

    display_name = models.CharField(max_length=150)

    department = models.CharField(
        max_length=150,
        blank=True,
    )

    class Meta:
        verbose_name = "Instructor profile"
        verbose_name_plural = "Instructor profiles"
        ordering = ["display_name"]

    def __str__(self):
        """Return a readable representation of the instructor."""
        return self.display_name


class StudentProfile(models.Model):
    """
    Profile information for a student.

    The student has an explicitly defined primary key. The associated user
    account provides authentication, while this model stores student-specific
    information.

    Fields
    ------
    student_id:
        Explicit primary key for the student profile.
    user:
        User account associated with the student.
    display_name:
        Name displayed in course rosters and attendance reports.
    student_number:
        Optional institutional student number.
    """

    student_id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    display_name = models.CharField(max_length=150)

    student_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Student profile"
        verbose_name_plural = "Student profiles"
        ordering = ["display_name"]

    def __str__(self):
        """Return a readable representation of the student."""
        return self.display_name


class Course(models.Model):
    """
    A course taught by an instructor.

    A course has exactly one instructor and may have many enrolled students
    through the Enrollment model. Each course can contain multiple lectures.

    The meeting_schedule field is intentionally stored as descriptive text
    (for example, 'Monday and Wednesday, 10:00-11:30 AM') to accommodate
    schedules that do not follow a uniform structure.

    For machine-readable recurring schedules, consider a separate schedule
    model with weekday, start_time, end_time, and timezone fields.

    Fields
    ------
    course_id:
        Explicit primary key for the course.
    name:
        Human-readable course name.
    instructor:
        Instructor responsible for teaching the course.
    meeting_schedule:
        Description of the course's regular meeting times.
    description:
        Optional longer description of the course.
    created_at:
        Timestamp when the course record was created.
    """

    course_id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=200)

    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    meeting_schedule = models.CharField(
        max_length=500,
        help_text=(
            "For example: Monday and Wednesday, 10:00-11:30 AM."
        ),
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    students = models.ManyToManyField(
        StudentProfile,
        through="Enrollment",
        related_name="courses",
    )

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ["name"]

    def __str__(self):
        """Return the course name and its identifier."""
        return f"{self.name} ({self.course_id})"

    def enrolled_student_count(self):
        """Return the number of students currently enrolled in this course."""
        return self.enrollments.count()


class Enrollment(models.Model):
    """
    Join table connecting students and courses.

    Each enrollment represents the membership of one student in one course.

    The composite primary key consists of student_id and course_id. This
    prevents duplicate enrollment records for the same student-course pair
    without requiring a separate surrogate primary key.

    Both student and course reference models with explicitly defined primary
    keys. The strings passed to CompositePrimaryKey refer to the local field
    names on this model, not to fields on the related models.

    Fields
    ------
    student:
        Student associated with the enrollment.
    course:
        Course in which the student is enrolled.
    enrolled_at:
        Timestamp when the enrollment was created.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    pk = models.CompositePrimaryKey("student_id", "course_id")

    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        ordering = ["course_id", "student_id"]

    def __str__(self):
        """Return the student-course relationship."""
        return f"Student {self.student_id} enrolled in course {self.course_id}"


class Lecture(models.Model):
    """
    An individual lecture or class session within a course.

    Each lecture belongs to exactly one course and has a scheduled date and
    a unique QR identifier. The QR identifier can be encoded into a QR code
    for students to scan during attendance taking.

    The QR identifier is a random UUID rather than a sequential database ID.
    It should still be validated by the attendance endpoint and should not
    be treated as sufficient authorization by itself.

    Fields
    ------
    lecture_id:
        Explicit primary key for the lecture.
    course:
        Course to which the lecture belongs.
    lecture_date:
        Date and time at which the lecture is scheduled to take place.
    qr_identifier:
        Unique identifier associated with the lecture's QR code.
    topic:
        Optional title or subject of the lecture.
    created_at:
        Timestamp when the lecture record was created.
    """

    lecture_id = models.BigAutoField(primary_key=True)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lectures",
    )

    lecture_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    qr_identifier = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    topic = models.CharField(
        max_length=200,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lecture"
        verbose_name_plural = "Lectures"
        ordering = ["lecture_date"]

    def __str__(self):
        """Return the course and lecture date."""
        return f"{self.course.name} — {self.lecture_date:%Y-%m-%d %H:%M}"

    def regenerate_qr_identifier(self):
        """
        Generate and save a new QR identifier.

        Use this if an existing QR identifier needs to be invalidated.
        Regeneration should be coordinated with any QR images already
        distributed to students.
        """
        self.qr_identifier = uuid.uuid4()
        self.save(update_fields=["qr_identifier"])
        return self.qr_identifier


class QRCodeUpload(models.Model):
    """
    A record of a student's QR-code submission for attendance.

    Each upload is associated with a student and may optionally reference
    the lecture identified by the scanned QR code.

    The lecture relationship is nullable to support workflows in which a
    QR submission is stored before the system determines which lecture it
    belongs to.

    This model records a submission; it does not automatically establish
    verified attendance. The application should validate the QR identifier,
    lecture eligibility, enrollment, and duplicate submissions before
    accepting attendance.

    Fields
    ------
    upload_id:
        Explicit primary key for the upload record.
    student:
        Student who submitted the QR code.
    lecture:
        Optional lecture associated with the submission.
    scanned_qr_identifier:
        QR identifier received from the client, if available.
    uploaded_at:
        Timestamp when the submission was recorded.
    """

    upload_id = models.BigAutoField(primary_key=True)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_uploads",
    )

    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        related_name="qr_uploads",
        null=True,
        blank=True,
    )

    scanned_qr_identifier = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifier read from the submitted QR code.",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "QR code upload"
        verbose_name_plural = "QR code uploads"
        ordering = ["-uploaded_at"]

    def __str__(self):
        """Return a readable description of the submission."""
        return (
            f"QR upload by {self.student} "
            f"at {self.uploaded_at:%Y-%m-%d %H:%M}"
        )

    def matches_lecture_qr(self):
        """
        Check whether the submitted QR identifier matches the linked lecture.

        Returns False if either the lecture or the scanned identifier is
        missing. This checks identifier consistency only; it does not verify
        enrollment, submission timing, or attendance eligibility.
        """
        if self.lecture is None or self.scanned_qr_identifier is None:
            return False

        return self.scanned_qr_identifier == self.lecture.qr_identifier

    def clean(self):
        """
        Validate consistency between the upload, student enrollment,
        and linked lecture.

        If a lecture is specified, the student must be enrolled in the
        course to which that lecture belongs. If a scanned QR identifier is
        also specified, it must match the linked lecture.

        Django does not automatically call full_clean() on every save().
        Call it explicitly in application workflows that require validation.
        """
        super().clean()

        if self.lecture_id is None:
            return

        errors = {}

        if (
            self.scanned_qr_identifier is not None
            and self.scanned_qr_identifier != self.lecture.qr_identifier
        ):
            errors["scanned_qr_identifier"] = (
                "The scanned QR identifier does not match the selected lecture."
            )

        is_enrolled = Enrollment.objects.filter(
            student_id=self.student_id,
            course_id=self.lecture.course_id,
        ).exists()

        if self.student_id is not None and not is_enrolled:
            errors["student"] = (
                "The student must be enrolled in the lecture's course."
            )

        if errors:
            raise ValidationError(errors)
