# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'InstanceType'
        db.create_table('biocloudcentral_instancetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('cloud', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['biocloudcentral.Cloud'])),
            ('pretty_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('tech_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('biocloudcentral', ['InstanceType'])


    def backwards(self, orm):
        
        # Deleting model 'InstanceType'
        db.delete_table('biocloudcentral_instancetype')


    models = {
        'biocloudcentral.cloud': {
            'Meta': {'ordering': "['cloud_type']", 'object_name': 'Cloud'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'bucket_default': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cidr_range': ('django.db.models.fields.CharField', [], {'max_length': '25', 'null': 'True', 'blank': 'True'}),
            'cloud_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'ec2_conn_path': ('django.db.models.fields.CharField', [], {'default': "'/'", 'max_length': '255'}),
            'ec2_port': ('django.db.models.fields.IntegerField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_secure': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'region_endpoint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'region_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            's3_conn_path': ('django.db.models.fields.CharField', [], {'default': "'/'", 'max_length': '255'}),
            's3_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            's3_port': ('django.db.models.fields.IntegerField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'biocloudcentral.image': {
            'Meta': {'ordering': "['cloud']", 'object_name': 'Image'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Cloud']"}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'kernel_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'ramdisk_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'biocloudcentral.instancetype': {
            'Meta': {'ordering': "['cloud']", 'object_name': 'InstanceType'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Cloud']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tech_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['biocloudcentral']
