# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Species'
        db.create_table(u'djff_species', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('species_name', self.gf('django.db.models.fields.CharField')(default='full name of fish species', max_length=200)),
            ('species_shortname', self.gf('django.db.models.fields.CharField')(default='ABC', max_length=200)),
            ('sample_image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'djff', ['Species'])

        # Adding model 'Experiment'
        db.create_table(u'djff_experiment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_name', self.gf('django.db.models.fields.CharField')(default='New Experiment', max_length=250)),
            ('experiment_start_dtg', self.gf('django.db.models.fields.DateTimeField')()),
            ('species', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djff.Species'])),
            ('researcher_name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('researcher_email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
        ))
        db.send_create_signal(u'djff', ['Experiment'])

        # Adding model 'Image'
        db.create_table(u'djff_image', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djff.Experiment'])),
            ('dtg_capture', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2014, 8, 27, 0, 0))),
            ('voltage', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('image_file', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('is_cal_image', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'djff', ['Image'])

        # Adding model 'ImageAnalysis'
        db.create_table(u'djff_imageanalysis', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djff.Image'])),
            ('analysis_dtg', self.gf('django.db.models.fields.DateTimeField')()),
            ('orientation', self.gf('django.db.models.fields.SmallIntegerField')(default=None)),
            ('location', self.gf('djff.fields.LocationField')(default=0)),
            ('silhouette', self.gf('djff.fields.ContourField')(default=0)),
            ('verified_dtg', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('verified_by', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'djff', ['ImageAnalysis'])

        # Adding model 'HopperChain'
        db.create_table(u'djff_hopperchain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hopperchain_name', self.gf('django.db.models.fields.CharField')(max_length=250, blank=True)),
            ('hopperchain_spec', self.gf('djff.fields.HopperchainSpecField')()),
        ))
        db.send_create_signal(u'djff', ['HopperChain'])


    def backwards(self, orm):
        # Deleting model 'Species'
        db.delete_table(u'djff_species')

        # Deleting model 'Experiment'
        db.delete_table(u'djff_experiment')

        # Deleting model 'Image'
        db.delete_table(u'djff_image')

        # Deleting model 'ImageAnalysis'
        db.delete_table(u'djff_imageanalysis')

        # Deleting model 'HopperChain'
        db.delete_table(u'djff_hopperchain')


    models = {
        u'djff.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'experiment_name': ('django.db.models.fields.CharField', [], {'default': "'New Experiment'", 'max_length': '250'}),
            'experiment_start_dtg': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'researcher_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'researcher_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'species': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djff.Species']"})
        },
        u'djff.hopperchain': {
            'Meta': {'object_name': 'HopperChain'},
            'hopperchain_name': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'hopperchain_spec': ('djff.fields.HopperchainSpecField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djff.image': {
            'Meta': {'object_name': 'Image'},
            'dtg_capture': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 8, 27, 0, 0)'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djff.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'is_cal_image': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
        },
        u'djff.species': {
            'Meta': {'object_name': 'Species'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sample_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'species_name': ('django.db.models.fields.CharField', [], {'default': "'full name of fish species'", 'max_length': '200'}),
            'species_shortname': ('django.db.models.fields.CharField', [], {'default': "'ABC'", 'max_length': '200'})
        }
    }

    complete_apps = ['djff']