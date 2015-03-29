# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Flavor'
        db.create_table('biocloudcentral_flavor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['biocloudcentral.Image'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('user_data', self.gf('django.db.models.fields.CharField')(max_length=16384)),
            ('default', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('biocloudcentral', ['Flavor'])


    def backwards(self, orm):

        # Deleting model 'Flavor'
        db.delete_table('biocloudcentral_flavor')


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
        'biocloudcentral.databucket': {
            'Meta': {'ordering': "['cloud', 'name']", 'object_name': 'DataBucket'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Cloud']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '63'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'biocloudcentral.flavor': {
            'Meta': {'ordering': "['cloud', 'image']", 'object_name': 'Flavor'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Image']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user_data': ('django.db.models.fields.CharField', [], {'max_length': '16384'})
        },
        'biocloudcentral.image': {
            'Meta': {'ordering': "['cloud']", 'object_name': 'Image'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Cloud']"}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'kernel_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'ramdisk_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'biocloudcentral.instancetype': {
            'Meta': {'ordering': "['cloud', '-updated']", 'object_name': 'InstanceType'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['biocloudcentral.Cloud']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tech_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'biocloudcentral.usage': {
            'Meta': {'ordering': "['updated', 'cloud_type']", 'object_name': 'Usage'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'cloud_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'cloud_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'instance_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['biocloudcentral']
