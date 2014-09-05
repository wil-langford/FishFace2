from django.contrib import admin
from djff import models


class ImageInline(admin.TabularInline):
    model = models.Image


class ExperimentAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Experiment Information', {
            'fields': [
                'name',
                'xp_start',
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
        'name',
        'xp_start',
        'researcher_name'
    )
    list_filter = [
        'xp_start',
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
                'capture_timestamp',
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
        'capture_timestamp',
        'is_cal_image',
        'xp',
        'cjr',
        'inline_image'
    )
    list_filter = ('capture_timestamp',)

admin.site.register(models.Image, ImageAdmin)


class SpeciesAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Species Information', {
            'fields': [
                'name',
                'shortname',
            ]
        }),
        ('Sample image', {
            'fields': [
                'image',
            ]
        }),
    ]
    list_display = ('name', 'shortname', 'inline_image')

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