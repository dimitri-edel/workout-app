from django.db import models
from django.contrib.auth.models import User

# EXERCISE_TYPE is used in class Exercise
EXERCISE_TYPE = ((0, "Strength"), (1, "Cardio"))

# A class for a Workout session
# A Wrokout is comprised of several sets.
# Each set is for one particular type of exercise
class Workout(models.Model):
    # Relation to the user
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_workout")
    # Name of the session
    name = models.CharField(max_length=200, blank=False)
    # Date on which the workout took place
    date = models.DateTimeField(auto_now_add=True)
    # Meta for ordering the objects in a descending order
    class Meta:
        ordering = ['-date']
    # Strinbg representation of the object
    def __str__(self):
        return self.name

# A class for the type of exercise, such as push-ups, pull-ups, jogging, etc.
# The WorkoutSet class is related to this class. A WorkoutSet is for a particular
# type of exercise. For instance, the user wants to do a set of push-ups. 
class Exercise(models.Model):
    # Name of the exercise
    name = models.CharField(max_length=200, blank=False)
    # Type of exercise. There are only two types: Strength and Cardio which are
    # defined in a tupple at the top of this script file
    type = models.IntegerField(choices=EXERCISE_TYPE, default=0)
    # The goal field will only be used in conjunction with Exercises of type Cardio.
    # If the Exercise if of type Strength then this field will be left blank.
    # There are basicly two types of goal: distance and repetitions.
    goal = models.CharField(max_length=12, blank=True)
    # Strinbg representation of the object
    def __str__(self):
        return self.name

# A class for a set. It belongs to (related to) an object of type Workout.
# Each set must also be related to a particular exercise, such as pull-ups or jogging, etc.
class ExerciseSet(models.Model):
    # The relationshop to the owner object of type Workout
    workout = models.ForeignKey(
        Workout, on_delete=models.CASCADE, related_name="workout_set")
    # The relationship to an Exercise object
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="exercise_set")
    # Number of repetitioons in this set
    reps = models.IntegerField(blank=True, null=True, default="0")
    # The weight that was used, if weight lifting is involved
    weight = models.IntegerField(blank=True, null=True, default="0")
    # The time it took to complete the set, if it is a cardio exercise
    time = models.IntegerField(blank=True, null=True, default="0")
    # The distance covered in the ammount of time specified in the time field
    distance = models.FloatField(blank=True, null=True, default="0")
