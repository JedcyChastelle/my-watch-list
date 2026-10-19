from django.db import models


class Task(models.Model):
    title = models.CharField(max_length=200)
    complete = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    tmdb_id = models.IntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.title