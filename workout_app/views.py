from django.shortcuts import render, get_object_or_404, reverse
from django.views import generic, View
from django.http import HttpResponseRedirect
from .models import *
from .forms import *
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import ProtectedError
from django.core.paginator import Paginator
from .helpers import redirect_user_to_goup

# The follwing two reports are used by WorkoutList view
# They are the items that get displayed when the user navigates to 'Workouts'
# They are used in the template workout_list.html to enable displaying the name of the workout
# and providing a link to the workout by using its id.
# Also, the reports store summaries of each exercise in the workout.
# And hold the id of WorkoutExercise, which can be used to provide a link to the WorkoutExercise
# with all of its ExerciseSets
class WorkoutReport:
    # A class for storing reports for each workout
    workout_id = 0
    date = None
    name = None
    exercise_reports = None

    def __init__(self) -> None:
        self.date = "today"
        self.name = "workout name"
        self.exercise_reports = []


class ExerciseReport:
    # A class for storing reports about an exercise in a workout
    workout_exercise_id = 0
    report = ""


class HomePage(View):
    # View for the home page
    template_name = "index.html"

    def get(self, request, *args, **kwargs):
        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)

        return render(request, self.template_name)


class WorkoutList(View):
    # List of Workouts

    model = Workout
    template_name = "workout_list.html"
    paginate_by = 2
    # Constants for exercise.type
    STRENGTH = 0
    CARDIO = 1
    # Constants for exercise.goal
    REPETITIONS = 0
    DISTANCE = 1

    def get(self, request, *args, **kwargs):
        # If the user is not logged in, then redirect them to the login page
        if not request.user.is_authenticated:
            return HttpResponseRedirect("accounts/login/")

        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)

        # Only retrieve datasets related to the user
        self.model.objects.filter(user_id=self.request.user.id)
        # Generate Roports
        reports = self.__generate_reports()
        # Create paginator and load it with reports
        paginator = Paginator(reports, self.paginate_by)
        # Retrieve page number from the GET-Request-object
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context = {
            "page_obj": page_obj,
        }
        return render(request, self.template_name, context=context)

    # Create Reports

    def __generate_reports(self):
        reports = []
        workout_list = self.model.objects.filter(user_id=self.request.user.id)
        for workout in workout_list:
            # Create w wokrout report for each workout
            workout_exercises = WorkoutExercise.objects.filter(
                workout_id=workout.id)
            report = WorkoutReport()
            report.workout_id = workout.id
            report.date = workout.date
            report.name = workout.name

            for workout_exercise in workout_exercises:
                # Create an exercise report for each exercise
                # and attach it to the workout report
                exercise_report = ExerciseReport()
                exercise_report.workout_exercise_id = workout_exercise.id
                exercise_report.report += f"{workout_exercise.exercise.name}:"
                exercise_report.report += self.__generate_report(
                    workout_exercise)
                report.exercise_reports.append(exercise_report)

            reports.append(report)
        return reports

    def __generate_report(self, workout_exercise):
        # generate a report according to the type and goal of an exercise
        report = ""
        exercise_sets = ExerciseSet.objects.filter(
            workout_exercise_id=workout_exercise.id)

        if workout_exercise.exercise.type == self.STRENGTH:
            # Get a summarized report for strength exercises
            report += self.__generate_strength_report(exercise_sets)

        else:
            if workout_exercise.exercise.goal == self.REPETITIONS:
                # Get a summarized report for cardio exercises with repetitions
                report += self.__generate_repetitions_report(exercise_sets)
            else:
                # Get a summarized report for cardio exercises with distance
                report += self.__generate_distance_report(exercise_sets)

        return report

    def __generate_strength_report(self, exercise_sets):
        # Summarize all the sets in a single report for an exercise for strength
        report = ""
        for exercise_set in exercise_sets:
            report += f"{exercise_set.reps} x {exercise_set.weight} kg  "

        return report

    def __generate_repetitions_report(self, exercise_sets):
        # Summarize all the sets in a single report for cardio exercise with repetitions
        report = ""
        for exercise_set in exercise_sets:
            report += f"{exercise_set.reps} in {exercise_set.time}     "

        return report

    def __generate_distance_report(self, exercise_sets):
        # Summarize all the sets in a single report for an exercise with distance
        report = ""
        for exercise_set in exercise_sets:
            report += f"{exercise_set.distance} in {exercise_set.time}   "

        return report


class AddWorkout(View):
    # View for adding a new Workout

    # Reference to the form class for the model class Workout
    workout_form_class = WorkoutForm
    # Referenece to the form class for the model class ExerciseSet
    workout_exercise_form_class = WorkoutExerciseForm
    # Referenece to the template for this view
    template_name = "add_workout.html"
    # Process a GET-Request

    def get(self, request, *args, **kwargs):
        # If the user is not logged in, then redirect them to the login page
        if not request.user.is_authenticated:
            return HttpResponseRedirect("accounts/login/")

        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)
        # Instanciate the forms.
        # The prefix is mandatory whhen using several forms in the same view.
        # When initializing a form, using the data in the POST-request object, prefix
        # helps setting the forms apart, as you can see in the post method below.
        workout_form = self.workout_form_class(prefix="workout")
        workout_exercise_form = self.workout_exercise_form_class(user_id=request.user.id,
                                                                 prefix="workout_exercise")
        # Render the dedicated template
        return render(request, self.template_name, {"workout_form": workout_form, "workout_exercise_form": workout_exercise_form})
    # Process a POST-Request

    def post(self, request, *args, **kwargs):
        # Instanciate the forms.
        workout_form = self.workout_form_class(request.POST, prefix="workout")
        workout_exercise_form = self.workout_exercise_form_class(
            request.POST, user_id=request.user.id, prefix="workout_exercise")

        # If both forms are valid
        if workout_form.is_valid() and workout_exercise_form.is_valid():
            # Assign the form to the current user.
            # The instance property of the forms is a reference to the model class
            # that is being used and allows us to access its properties and methods
            workout_form.instance.user = request.user
            # Cimmit the model object to the database
            workout_form.save()
            # Assign the workout_id of the newly created Workout to the ExerciseSet.workout_id field
            workout_exercise_form.instance.workout_id = workout_form.instance.id
            # Commit the model object to the database
            workout_exercise_form.save()

            return HttpResponseRedirect(reverse("edit_workout", kwargs={'id': workout_form.instance.id}))

        # If the form was not valid, render the template. The workout_from will contain the validation
        # messages for the user, which had been generated upon calling the is_valid() method
        return render(request, self.template_name, {"workout_form": workout_form})


class EditWorkout(View):
    # class for editing the list of exercises that the workout is comprised of

    # Reference to the name of the form class for the model class Workout
    workout_form_class = WorkoutForm
    # Reference to the name of the form class for the model class WorkoutExercise
    workout_exercise_form_class = WorkoutExerciseForm

    # Referenece to the template for this view
    template_name = "edit_workout.html"
    # Process a GET-Request

    def get(self, request, *args, **kwargs):
        # If the user is not logged in, then redirect them to the login page
        if not request.user.is_authenticated:
            return HttpResponseRedirect("accounts/login/")

        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)
        # Pull the workout.id from kwargs
        id = kwargs['id']
        # Instanciate the forms.
        # The prefix is mandatory whhen using several forms in the same view.
        # When initializing a form, using the data in the POST-request object, prefix
        # helps setting the forms apart, as you can see in the post method below.
        workout = Workout.objects.get(id=id)
        # Create form for the workout object
        workout_form = self.workout_form_class(
            instance=workout, prefix="workout")

        workout_exercise_list = WorkoutExercise.objects.filter(
            workout_id=workout.id)
        # Create a form for the last WrokoutExercise object
        workout_exercise_form = self.workout_exercise_form_class(
            user_id=request.user.id, prefix="workout_exercise")

        # Render the dedicated template
        return render(
            request, self.template_name, {"workout_form": workout_form,
                                          "workout_exercise_list": workout_exercise_list,
                                          "workout_exercise_form": workout_exercise_form})

    def post(self, request, id, *args, **kwargs):
        # Process a POST-Request
        # @parameter : id = workout_id
        # Get the workout using the id parameter
        workout = Workout.objects.get(id=id)
        # Instanciate the forms.
        workout_form = self.workout_form_class(
            request.POST, prefix="workout", instance=workout)

        workout_exercise_form = self.workout_exercise_form_class(
            request.POST, user_id=request.user.id, prefix="workout_exercise")

        # if the workout form has changed yet the workout_exercise_form hasn't
        if workout_form.has_changed() and not workout_exercise_form.has_changed():
            if workout_form.is_valid():
                # Save the workout form only
                workout_form.save()
                return HttpResponseRedirect(reverse('edit_workout', kwargs={'id': workout_form.instance.id}))
        # If the workout form has not changed, yet the workout_exercise_form has
        elif workout_exercise_form.has_changed() and not workout_form.has_changed():
            if workout_exercise_form.is_valid():
                # Save the workout_exercise_form only
                return self.__save_workout_exercise_form(request, workout_form, workout_exercise_form)

        # In all other cases save both forms

        # If both forms are valid
        if workout_form.is_valid() and workout_exercise_form.is_valid():
            return self.__save_forms(request, workout_form, workout_exercise_form)

        # If the form was not valid, render the template. The workout_from will contain the validation
        # messages for the user, which had been generated upon calling the is_valid() method
        messages.add_message(
            request, messages.ERROR, "You might have forgotten to select the exercise you want to add!")
        workout_exercise_list = WorkoutExercise.objects.filter(
            workout_id=workout.id)

        return render(request, self.template_name, {"workout_form": workout_form, "workout_exercise_form": workout_exercise_form,
                                                    "workout_exercise_list": workout_exercise_list})

    def __save_workout_exercise_form(self, request, workout_form, workout_exercise_form):
        # Assign the form to the current user.
        # The instance property of the forms is a reference to the model class
        # that is being used and allows us to access its properties and methods
        workout_form.instance.user = request.user
        # Copy workout_id from the workout_form
        workout_exercise_form.instance.workout_id = workout_form.instance.id
        # Create a WorkoutExercise object and fill in the required fields, copying them from both forms
        workout_exercise = WorkoutExercise.objects.create(
            workout_id=workout_form.instance.id, exercise_id=workout_exercise_form.instance.exercise_id)
        workout_exercise.exercise_id = workout_exercise_form.instance.exercise_id
        workout_exercise.done = workout_exercise_form.instance.done
        # Save the object
        workout_exercise.save()

        return HttpResponseRedirect(reverse('edit_workout', kwargs={'id': workout_form.instance.id}))

    def __save_forms(self, request, workout_form, workout_exercise_form):
        # Assign the form to the current user.
        # The instance property of the forms is a reference to the model class
        # that is being used and allows us to access its properties and methods
        workout_form.instance.user = request.user
        # Cimmit the model object to the database
        workout_form.save()
        # Assign the workout_id of the newly created Workout to the ExerciseSet.workout_id field

        workout_exercise_form.instance.workout_id = workout_form.instance.id
        workout_exercise = WorkoutExercise.objects.create(
            workout_id=workout_form.instance.id, exercise_id=workout_exercise_form.instance.exercise_id)
        workout_exercise.exercise_id = workout_exercise_form.instance.exercise_id
        workout_exercise.done = workout_exercise_form.instance.done
        workout_exercise.save()

        return HttpResponseRedirect(reverse('edit_workout', kwargs={'id': workout_form.instance.id}))


class EditExerciseSet(View):
    workout_exercise_form_class = WorkoutExerciseForm
    exercise_set_form_class = ExerciseSetForm
    template_strength_exercise = "edit_workout_exercise_strength.html"
    template_repetitions_exercise = "edit_workout_exercise_repetitions.html"
    template_distance_exercise = "edit_workout_exercise_distance.html"
    EXERCISE_TYPE_STRENGTH = 0
    EXERCISE_TYPE_CARDIO = 1
    EXERCISE_GOAL_REPETITIONS = 0
    EXERCISE_GOAL_DISTANCE = 1

    def get(self, request, *args, **kwargs):
        # If the user is not logged in, then redirect them to the login page
        if not request.user.is_authenticated:
            return HttpResponseRedirect("accounts/login/")

        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)

        workout_exercise_id = kwargs["workout_exercise_id"]

        workout_exercise = WorkoutExercise.objects.get(id=workout_exercise_id)
        workout_exercise_form = self.workout_exercise_form_class(user_id=request.user.id,
                                                                 instance=workout_exercise, prefix="workout_exercise")

        # Empty form for adding a new set
        exercise_set_form = self.exercise_set_form_class(prefix="exercise_set")

        # Retrieve list of exercise_sets for the template
        exercise_set_list = ExerciseSet.objects.filter(
            workout_exercise_id=workout_exercise_id).order_by("id")

        # Retrieve exercise for the template
        exercise = Exercise.objects.get(
            id=workout_exercise.exercise_id)

        return self.__render(request, exercise, workout_exercise_form, exercise_set_form, exercise_set_list)

    def post(self, request, workout_exercise_id, *args, **kwargs):
        # Retrieve workout_exercise using the workout_exercise_id
        workout_exercise = WorkoutExercise.objects.get(id=workout_exercise_id)

        # Retrieve the workout_exercise_form from the request object
        workout_exercise_form = self.workout_exercise_form_class(
            request.POST, user_id=request.user.id, instance=workout_exercise, prefix="workout_exercise")
        # Retrieve the execise_set_form from the request oobject
        exercise_set_form = self.exercise_set_form_class(
            request.POST, prefix="exercise_set")
        # Retrieve an exercise object for the template
        exercise = Exercise.objects.get(id=workout_exercise.exercise_id)

        # If forms are valid
        if workout_exercise_form.is_valid() and exercise_set_form.is_valid():
            # Save the forms
            return self.__save_forms(request, workout_exercise_form,
                                     exercise_set_form)

        return self.__render(request, exercise, workout_exercise_form, exercise_set_form)

    def __save_forms(self, request, workout_exercise_form, exercise_set_form):
        # Save forms
        workout_exercise_form.instance.user = request.user
        workout_exercise_form.save()

        # Create a new object of type ExerciseSet
        exercise_set = ExerciseSet.objects.create(
            workout_exercise_id=workout_exercise_form.instance.id)
        # Copy fields from the form to the created object
        exercise_set.reps = exercise_set_form.instance.reps
        exercise_set.weight = exercise_set_form.instance.weight
        exercise_set.time = exercise_set_form.instance.time
        exercise_set.distance = exercise_set_form.instance.distance
        # Save the object
        exercise_set.save()

        return HttpResponseRedirect(reverse("edit_exercise_set", kwargs={"workout_exercise_id": workout_exercise_form.instance.id}))

    def __render(self, request, exercise, workout_exercise_form, exercise_set_form, exercise_set_list):
        # Render a template according to the type and goal of the exercise
        if exercise.type == self.EXERCISE_TYPE_STRENGTH:
            return render(request, self.template_strength_exercise, {"exercise": exercise, "workout_exercise_form": workout_exercise_form, "exercise_set_form": exercise_set_form, "exercise_set_list": exercise_set_list})
        else:
            if exercise.goal == self.EXERCISE_GOAL_REPETITIONS:
                return render(request, self.template_repetitions_exercise, {"exercise": exercise, "workout_exercise_form": workout_exercise_form, "exercise_set_form": exercise_set_form, "exercise_set_list": exercise_set_list})
            else:
                return render(request, self.template_distance_exercise, {"exercise": exercise, "workout_exercise_form": workout_exercise_form, "exercise_set_form": exercise_set_form, "exercise_set_list": exercise_set_list})


class AddExerciseSet(View):
    # Add an ExerciseSet to the workoout

    def get(self, request, workout_exercise_id, workout_id,  *args, **kwargs):
        # Process a GET-request

        # Create new ExerciseSet object
        ExerciseSet.objects.create(workout_exercise_id=workout_exercise_id)
        return HttpResponseRedirect(reverse('edit_exercise_set', kwargs={"workout_exercise_id": workout_exercise_id}))


class DeleteExerciseSet(View):
    # Delete an ExerciseSet from a workout
    def get(self, request, workout_exercise_id, exercise_set_id, *args, **kwargs):
        exercise_set = ExerciseSet.objects.get(id=exercise_set_id)
        exercise_set.delete()
        return HttpResponseRedirect(reverse('edit_exercise_set', kwargs={"workout_exercise_id": workout_exercise_id}))


class AddWorkoutExercise(View):
    def get(self, request, workout_id, *args, **kwargs):
        exercise = Exercise.objects.first()
        WorkoutExercise.objects.create(
            workout_id=workout_id, exercise_id=exercise.id)

        return HttpResponseRedirect(reverse('edit_workout', kwargs={"id": workout_id}))


class DeleteWorkoutExercise(View):
    def get(self, request, workout_exercise_id, workout_id, *args, **kwargs):
        workout_exercise = WorkoutExercise.objects.get(id=workout_exercise_id)
        workout_exercise.delete()
        return HttpResponseRedirect(reverse('edit_workout', kwargs={'id': workout_id}))


class DeleteWorkout(View):
    def get(self, request, workout_id, *args, **kwargs):
        workout = Workout.objects.get(id=workout_id)
        workout.delete()
        return HttpResponseRedirect(reverse('workout_list'))


class EditExerciseList(View):
    # Paginator - Number of items per page
    paginate_by = 5
    # Reference to the form
    exercise_form_class = ExerciseForm
    # Reference to the template
    template_name = "edit_exercise_list.html"
    # last id created
    # Process a GET-Request

    def get(self, request, *args, **kwargs):
        # If the user is not logged in, then redirect them to the login page
        if not request.user.is_authenticated:
            return HttpResponseRedirect("accounts/login/")

        # Check if the user belongs in a group and redirect them if they do
        if request.user.groups.exists():
            return redirect_user_to_goup(request=request)

        # Query the last exercises related to the current user
        exercises = Exercise.objects.filter(
            user_id=request.user.id).order_by('-id')

        # Pagination
        paginator = Paginator(exercises, self.paginate_by)
        # Retrieve page number from the GET-Request-object
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Instanciate the form
        # exercise_form = self.exercise_form_class(instance=edit_exercise)
        exercise_form = self.exercise_form_class()
        # Render the specified template
        return render(request, self.template_name, {"exercise_form": exercise_form, "page_obj": page_obj, })

    def post(self, request, *args, **kwargs):
        # Process a POST-Request
        # Instanciate the form
        exercise_form = self.exercise_form_class(
            request.POST)

        # If the form is valid
        if exercise_form.is_valid():
            # Assign the form to the current user.
            # The instance property of the forms is a reference to the model class
            # that is being used and allows us to access its properties and methods
            # Add append a new exercise to the list of exercises
            exercise = Exercise.objects.create(user_id=request.user.id)
            # copy fields from the form
            exercise.name = exercise_form.instance.name
            exercise.type = exercise_form.instance.type
            exercise.goal = exercise_form.instance.goal

            # Commit the model object to the database
            exercise.save()
            # Reverse back to the page with the list of exercises
            return HttpResponseRedirect(reverse("edit_exercise_list"))
        # If the form is invalid, in this case, it can only mean one thing: The name field is empty
        else:
            messages.add_message(request=request, level=messages.ERROR,
                                 message="You need to enter a Name for the exercise, before adding it!")
            return HttpResponseRedirect(reverse("edit_exercise_list"))


class DeleteExercise(View):
    # Delete an exercise from the list of available exercises
    def get(self, request, exercise_id, *args, **kwargs):
        exercise = Exercise.objects.get(id=exercise_id)
        try:
            exercise.delete()
        except ProtectedError:
            # ProtectedError is raised because if the exercise is used in a workout
            # In the model WorkoutExercise the foreign key to the exercise states  on_delete=models.PROTECT
            messages.add_message(
                request, messages.ERROR, "This exercise connot be deleted because it is being used in a workout!")

        return HttpResponseRedirect(reverse("edit_exercise_list"))


# List of Exercises
class ExerciseList(generic.ListView):
    model = Exercise
    queryset = Exercise.objects.all()
    template_name = "exercise_list.html"
    paginate_by = 1

    def get_queryset(self):
        # Only retrieve datasets related to the user
        return self.model.objects.filter(user_id=self.request.user.id)


# View for editing exercises
class EditExercise(View):
    # Reference to the form
    exercise_form_class = ExerciseForm
    # Reference to the template
    template_name = "edit_exercise.html"

    def get(self, request, *args, **kwargs):
        # Process a GET-Request
        exercise_id = kwargs["exercise_id"]
        # Retrieve dataset
        exercise = Exercise.objects.get(id=exercise_id)
        # Store the id of the last object in the session
        request.session["edit_exercise_id"] = exercise_id
        # Instanciate the form
        exercise_form = self.exercise_form_class(instance=exercise)
        # Render the specified template
        return render(request, self.template_name, {"exercise_form": exercise_form})
    # Process a POST-Request

    def post(self, request,  *args, **kwargs):
        # Retrieve the object using the id stored in session
        edit_exercise = Exercise.objects.get(
            id=request.session["edit_exercise_id"])
        # Instanciate the form
        exercise_form = self.exercise_form_class(
            request.POST, instance=edit_exercise)
        # If the form is valid
        if exercise_form.is_valid():
            # Assign the form to the current user.
            # The instance property of the forms is a reference to the model class
            # that is being used and allows us to access its properties and methods
            exercise_form.instance.user = request.user
            # Commit the model object to the database
            exercise_form.save()

            return HttpResponseRedirect(reverse("edit_exercise_list"))
        # If the form was not valid, render the template. The workout_from will contain the validation
        # messages for the user, which had been generated upon calling the is_valid() method
        return render(request, self.template_name, {"exercise_form": exercise_form})
