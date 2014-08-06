from django.contrib import admin
from djff import models

class ImageInline(admin.TabularInline):
    model = models.Image


class ExperimentAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Experiment Information', {
            'fields': [
                'experiment_name',
                'experiment_start_dtg',
                'experiment_last_viewed'
            ]
        })
    ]
    inlines = [ImageInline]
    list_display = ('experiment_name', 'experiment_start_dtg')
    list_filter = ['experiment_start_dtg']
    search_fields = ['question_text']

admin.site.register(models.Experiment, ExperimentAdmin)