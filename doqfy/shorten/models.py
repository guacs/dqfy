from django.db import models


class Url(models.Model):
    short_id = models.CharField(primary_key=True, max_length=20)
    long_url = models.TextField(db_index=True)

    def __str__(self) -> str:
        return f"{self.long_url} ({self.short_id})"
