from django.contrib import admin
from djff import models


class ImageInline(admin.TabularInline):
    model = models.Image


class CaptureJobRecordInline(admin.TabularInline):
    model = models.CaptureJobRecord


class ResearcherInline(admin.TabularInline):
    model = models.Researcher


class FishLocaleInline(admin.TabularInline):
    model = models.FishLocale


class ExperimentAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Experiment Information', {
            'fields': [
                'name',
                'xp_start',
                'species',
                'researcher'
            ]
        }),
    ]

    inlines = [CaptureJobRecordInline]
    list_display = (
        'name',
        'xp_start',
    )
    list_filter = [
        'xp_start',
        'species',
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
                'current',
                'is_cal_image',
                'normalized_image',
                'image_file',
            ]
        })
    ]
    # TODO: uncomment following line
    # inlines = [PowerSupplyLogInline]
    list_display = (
        'capture_timestamp',
        'voltage',
        'current',
        'is_cal_image',
        'xp',
        'cjr',
        'inline_image'
    )
    list_filter = ('capture_timestamp', 'xp', 'cjr')

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
                    'current',
                    'duration',
                    'interval',
                    'startup_delay',
                ]
            }
        ),
    ]

    list_display = (
        'voltage',
        'current',
        'duration',
        'interval',
        'startup_delay'
    )

    list_filter = ['duration', 'voltage']

admin.site.register(models.CaptureJobTemplate, CaptureJobTemplateAdmin)

class CaptureJobRecordAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Parameters', {
                'fields': [
                    'xp',
                    'voltage',
                    'current',
                    'job_start',
                    'job_stop',
                    'running',
                ]
            }
        ),
    ]

    list_display = (
        'full_slug',
        'voltage',
        'current',
        'running',
        'job_start',
        'job_stop',
    )

    list_filter = ['xp']

admin.site.register(models.CaptureJobRecord, CaptureJobRecordAdmin)


class ResearcherAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Researcher Information', {
                'fields': [
                    'name',
                    'email',
                ]
            }
        )
    ]

    list_display = (
        'name',
        'email',
    )

admin.site.register(models.Researcher, ResearcherAdmin)


class TankAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Tank Information', {
                'fields': [
                    'short_name',
                    'description',
                ]
            }
        )
    ]

    list_display = (
        'short_name',
        'description',
    )

admin.site.register(models.Tank, TankAdmin)


class FishAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'Fish Information', {
                'fields': [
                    'species',
                    'comment',
                ]
            }
        )
    ]

    list_display = (
        'species',
        'slug',
        'comment',
        'last_seen_in'
    )

    inlines = [FishLocaleInline]

admin.site.register(models.Fish, FishAdmin)
