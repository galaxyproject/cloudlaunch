# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Cloud'
        db.create_table('biocloudcentral_cloud', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('cloud_type', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('bucket_default', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('region_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('region_endpoint', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ec2_port', self.gf('django.db.models.fields.IntegerField')(max_length=6, null=True, blank=True)),
            ('ec2_conn_path', self.gf('django.db.models.fields.CharField')(default='/', max_length=255)),
            ('cidr_range', self.gf('django.db.models.fields.CharField')(max_length=25, null=True, blank=True)),
            ('is_secure', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('s3_host', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('s3_port', self.gf('django.db.models.fields.IntegerField')(max_length=6, null=True, blank=True)),
            ('s3_conn_path', self.gf('django.db.models.fields.CharField')(default='/', max_length=255)),
        ))
        db.send_create_signal('biocloudcentral', ['Cloud'])

        # Adding model 'Image'
        db.create_table('biocloudcentral_image', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('cloud', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['biocloudcentral.Cloud'])),
            ('image_id', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('default', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('kernel_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('ramdisk_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
        ))
        db.send_create_signal('biocloudcentral', ['Image'])


    def backwards(self, orm):
        
        # Deleting model 'Cloud'
        db.delete_table('biocloudcentral_cloud')

        # Deleting model 'Image'
        db.delete_table('biocloudcentral_image')


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
        }
    }

    complete_apps = ['biocloudcentral']
