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
                'is_cal_image',
                'image_file'
            ]
        })
    ]
    # TODO: uncomment following line
    # inlines = [ImageAnalysisInline]
    list_display = (
        'voltage',
        'dtg_capture',
        'is_cal_image',
        'experiment',
        'capturejob',
        'inline_image'
    )
    list_filter = ('dtg_capture',)

admin.site.register(models.Image, ImageAdmin)


class SpeciesAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Species Information', {
            'fields': [
                'species_name',
                'species_shortname',
            ]
        }),
        ('Sample image', {
            'fields': [
                'sample_image',
            ]
        }),
    ]
    list_display = ('species_name', 'species_shortname', 'inline_image')

admin.site.register(models.Species, SpeciesAdmin)


class CaptureJobTemplateAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Parameters', {
                'fields': [
                    'voltage',
                    'duration',
                    'interval',
                    'startup_delay',
                ]
            }
        ),
    ]

    list_display = (
        'voltage',
        'duration',
        'interval',
        'startup_delay'
    )

admin.site.register(models.CaptureJobTemplate, CaptureJobTemplateAdmin)

class CaptureJobRecordAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Parameters', {
                'fields': [
                    'xp',
                    'voltage',
                    'job_start',
                    'job_stop',
                    'running',
                ]
            }
        ),
    ]

    list_display = (
        'xp',
        'voltage',
        'running',
        'job_start',
        'job_stop',
    )

admin.site.register(models.CaptureJobRecord, CaptureJobRecordAdmin)