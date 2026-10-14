import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task
from .tmdb import PROVIDERS, TMDBUnavailable, discover_top_series

logger = logging.getLogger("tasks.views")


@login_required
def index(request):
    tasks = Task.objects.filter(user=request.user).order_by("-created")
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
        return redirect("list")

    context = {"tasks": tasks, "form": form}
    return render(request, "tasks/list.html", context)


@login_required
def updateTask(request, pk):
    task = get_object_or_404(Task, id=pk, user=request.user)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("list")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


@login_required
def deleteTask(request, pk):
    item = get_object_or_404(Task, id=pk, user=request.user)

    if request.method == "POST":
        item.delete()
        return redirect("list")

    context = {"item": item}
    return render(request, "tasks/delete.html", context)


@login_required
@require_POST
def add_series(request, provider):
    if provider not in PROVIDERS:
        raise Http404("Plateforme inconnue")
    info = PROVIDERS[provider]

    # Les ID TMDB déjà présents dans MA watchlist
    existing_ids = set(
        Task.objects.filter(user=request.user)
        .exclude(tmdb_id=None)
        .values_list("tmdb_id", flat=True)
    )

    added = 0
    page = 1
    try:
        while added < 10:
            data = discover_top_series(info["id"], page)
            for serie in data["results"]:
                if serie["id"] in existing_ids:
                    continue  # déjà dans la watchlist : on passe à la suivante
                Task.objects.create(
                    user=request.user,
                    title=serie["name"],
                    tmdb_id=serie["id"],
                    provider=info["label"],
                )
                existing_ids.add(serie["id"])
                added += 1
                if added == 10:
                    break
            if page >= data["total_pages"]:
                break  # TMDB n'a plus de séries à proposer
            page += 1
    except TMDBUnavailable:
        messages.error(
            request,
            f"Le catalogue {info['label']} est momentanément indisponible. "
            "Votre watchlist reste accessible, réessayez dans quelques instants.",
        )
        if added:
            messages.info(request, f"{added} série(s) ont quand même été ajoutées.")
        return redirect("list")

    messages.success(request, f"{added} série(s) {info['label']} ajoutée(s) à votre watchlist.")
    return redirect("list")


def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("list")
    return render(request, "registration/signup.html", {"form": form})