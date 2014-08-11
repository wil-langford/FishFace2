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


class ImageAnalysisInline(admin.TabularInline):
    model = models.ImageAnalysis


class ImageAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Image Information', {
            'fields': [
                'dtg_capture',
                'species',
                'voltage',
                'filename',
            ]
        })
    ]
    inlines = [ImageAnalysisInline]
    list_display = ('species', 'voltage', 'dtg_capture')
    list_filter = ('species', 'dtg_capture')

admin.site.register(models.Image, ImageAdmin)