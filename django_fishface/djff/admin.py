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
                'species'
            ]
        }),
        ('Researcher (optional)', {
            'fields': [
                'researcher_name',
                'researcher_email'
            ]
        })
    ]
    inlines = [ImageInline]
    list_display = (
        'experiment_name',
        'experiment_start_dtg',
        'researcher_name'
    )
    list_filter = [
        'experiment_start_dtg',
        'species',
        'researcher_name'
    ]
    search_fields = ['question_text']

admin.site.register(models.Experiment, ExperimentAdmin)


class ImageAnalysisInline(admin.TabularInline):
    model = models.ImageAnalysis


class ImageAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Image Information', {
            'fields': [
                'dtg_capture',
                'voltage',
                'image_file'
            ]
        })
    ]
    inlines = [ImageAnalysisInline]
    list_display = ('voltage', 'dtg_capture')
    list_filter = ('dtg_capture',)

admin.site.register(models.Image, ImageAdmin)