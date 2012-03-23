# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Cloud.cidr_range'
        db.add_column('biocloudcentral_cloud', 'cidr_range', self.gf('django.db.models.fields.CharField')(max_length=25, null=True, blank=True), keep_default=False)

        # Changing field 'Cloud.ec2_port'
        db.alter_column('biocloudcentral_cloud', 'ec2_port', self.gf('django.db.models.fields.CharField')(max_length=6, null=True))

        # Changing field 'Cloud.s3_port'
        db.alter_column('biocloudcentral_cloud', 's3_port', self.gf('django.db.models.fields.CharField')(max_length=6, null=True))

        # Adding field 'Image.kernel_id'
        db.add_column('biocloudcentral_image', 'kernel_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True), keep_default=False)

        # Adding field 'Image.ramdisk_id'
        db.add_column('biocloudcentral_image', 'ramdisk_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Cloud.cidr_range'
        db.delete_column('biocloudcentral_cloud', 'cidr_range')

        # Changing field 'Cloud.ec2_port'
        db.alter_column('biocloudcentral_cloud', 'ec2_port', self.gf('django.db.models.fields.CharField')(default='', max_length=6))

        # User chose to not deal with backwards NULL issues for 'Cloud.s3_port'
        raise RuntimeError("Cannot reverse this migration. 'Cloud.s3_port' and its values cannot be restored.")

        # Deleting field 'Image.kernel_id'
        db.delete_column('biocloudcentral_image', 'kernel_id')

        # Deleting field 'Image.ramdisk_id'
        db.delete_column('biocloudcentral_image', 'ramdisk_id')


    models = {
        'biocloudcentral.cloud': {
            'Meta': {'ordering': "['cloud_type']", 'object_name': 'Cloud'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'bucket_default': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cidr_range': ('django.db.models.fields.CharField', [], {'max_length': '25', 'null': 'True', 'blank': 'True'}),
            'cloud_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'ec2_conn_path': ('django.db.models.fields.CharField', [], {'default': "'/'", 'max_length': '255'}),
            'ec2_port': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_secure': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'region_endpoint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'region_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            's3_conn_path': ('django.db.models.fields.CharField', [], {'default': "'/'", 'max_length': '255'}),
            's3_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            's3_port': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
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
