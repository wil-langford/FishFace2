# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Experiment'
        db.create_table(u'djff_experiment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_name', self.gf('django.db.models.fields.CharField')(max_length=250, null=True)),
            ('experiment_start_dtg', self.gf('django.db.models.fields.DateTimeField')()),
            ('experiment_last_viewed', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'djff', ['Experiment'])

        # Adding model 'Image'
        db.create_table(u'djff_image', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djff.Experiment'])),
            ('dtg_capture', self.gf('django.db.models.fields.DateTimeField')()),
            ('species', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('voltage', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('filename', self.gf('django.db.models.fields.FilePathField')(max_length=100, null=True, blank=True)),
            ('orientation', self.gf('django.db.models.fields.SmallIntegerField')(default=None, null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.CommaSeparatedIntegerField')(max_length=20, null=True, blank=True)),
            ('verified_dtg', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('verified_by', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'djff', ['Image'])


    def backwards(self, orm):
        # Deleting model 'Experiment'
        db.delete_table(u'djff_experiment')

        # Deleting model 'Image'
        db.delete_table(u'djff_image')


    models = {
        u'djff.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'experiment_last_viewed': ('django.db.models.fields.DateTimeField', [], {}),
            'experiment_name': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'experiment_start_dtg': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djff.image': {
            'Meta': {'object_name': 'Image'},
            'dtg_capture': ('django.db.models.fields.DateTimeField', [], {}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djff.Experiment']"}),
            'filename': ('django.db.models.fields.FilePathField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'orientation': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'species': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'verified_by': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'verified_dtg': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'voltage': ('django.db.models.fields.FloatField', [], {'default': '0'})
        }
    }

    complete_apps = ['djff']