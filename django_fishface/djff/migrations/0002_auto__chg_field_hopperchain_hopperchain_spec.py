# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'HopperChain.hopperchain_spec'
        db.alter_column(u'djff_hopperchain', 'hopperchain_spec', self.gf('djff.fields.HopperchainSpecField')())

    def backwards(self, orm):

        # Changing field 'HopperChain.hopperchain_spec'
        db.alter_column(u'djff_hopperchain', 'hopperchain_spec', self.gf('django.db.models.fields.TextField')())

    models = {
        u'djff.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'experiment_last_viewed': ('django.db.models.fields.DateTimeField', [], {}),
            'experiment_name': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'experiment_start_dtg': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djff.hopperchain': {
            'Meta': {'object_name': 'HopperChain'},
            'hopperchain_name': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'hopperchain_spec': ('djff.fields.HopperchainSpecField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djff.image': {
            'Meta': {'object_name': 'Image'},
            'dtg_capture': ('django.db.models.fields.DateTimeField', [], {}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djff.Experiment']"}),
            'filename': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'species': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voltage': ('django.db.models.fields.FloatField', [], {'default': '0'})
        },
        u'djff.imageanalysis': {
            'Meta': {'object_name': 'ImageAnalysis'},
            'analysis_dtg': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djff.Image']"}),
            'location': ('djff.fields.LocationField', [], {'default': '0'}),
            'orientation': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None'}),
            'silhouette': ('djff.fields.ContourField', [], {'default': '0'}),
            'verified_by': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'verified_dtg': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['djff']