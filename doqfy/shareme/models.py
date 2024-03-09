from django.db import models


class Snippet(models.Model):
    snippet_id = models.CharField(primary_key=True, max_length=20)
    snippet = models.TextField()
