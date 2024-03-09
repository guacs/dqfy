from django.db import models


class Snippet(models.Model):
    snippet_id = models.CharField(primary_key=True, max_length=20)
    snippet = models.TextField()
    encrypted = models.BooleanField(default=False)
    salt = models.BinaryField(max_length=16, default=None, null=True)

    def __str__(self) -> str:
        return f"Snippet(snippet_id={self.snippet_id}, snippet={self.snippet}, encrypted={self.encrypted})"
