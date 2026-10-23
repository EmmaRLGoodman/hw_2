"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User

import logging
import string
import random

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------
class InstructorProfile(models.Model):
    """Holds instructors, which have an ID and a user account for their other info"""
    Instructor_ID = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class StudentProfile(models.Model):
    """Holds students, which have an ID and a user account for their other info"""
    Student_ID = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class Course(models.Model):
    """Holds courses, which are linked to an instructor that teaches them.
    Nulls rather than cascades on instructor delete to account for, say,
    knowing a course will be held, the original instructor is unable to teach it,
    but the university does not yet know who will be teaching in their place."""
    Course_ID = models.IntegerField(primary_key=True)
    Name = models.CharField(max_length=70)
    Instructor = models.ForeignKey(InstructorProfile, on_delete=models.SET_NULL,
                                   null=True)
    Schedule = models.CharField(max_length=120)

# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------
class Enrollment(models.Model):
    """Holds enrollment, which allows for the many-to-many relationship between
    students and classes (many students in one class, each student takes many
    classes) and uses a composite primary key."""
    Student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("Student_id", "Course_id")

# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
class Lecture(models.Model):
    """Holds lectures, which have an ID, a course they are a lecture for,
    and a date they happen on"""
    QR_ID = models.IntegerField(primary_key=True)
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Date = models.DateField()


# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------
class QRCodeUpload(models.Model):
    """Holds QR codes uploaded by students - the lecture can be blank, allowing
    for a student to upload a QR code even if it is not recognized to be an 
    existing lecture."""
    Upload_ID = models.IntegerField(primary_key=True)
    Image = models.ImageField()
    Timestamp = models.DateTimeField(auto_now_add=True)
    Student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    Lecture = models.ForeignKey(Lecture, on_delete = models.SET_NULL, blank=True, null=True)



# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------



