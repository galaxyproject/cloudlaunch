# Generated by Django 2.1.7 on 2019-03-10 08:17

from django.db import migrations, models
import django.db.models.deletion
import smart_selects.db_fields


def copy_cloud_image_data(apps, schema_editor):
    Image = apps.get_model('cloudlaunch', 'Image')
    CloudImage = apps.get_model('cloudlaunch', 'CloudImage')
    Region = apps.get_model('djcloudbridge', 'Region')

    for cloud_image in CloudImage.objects.all():
        image = Image.objects.get(id=cloud_image.image_ptr_id)
        image.region = Region.objects.get(cloud=cloud_image.cloud)
        image.save()


class Migration(migrations.Migration):

    dependencies = [
        ('djcloudbridge', '0007_delete_cloudold'),
        ('cloudlaunch', '0008_match_djcloudbridge_and_introduce_targets'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='djcloudbridge.Region'),
        ),
        migrations.AlterField(
            model_name='applicationversioncloudconfig',
            name='image',
            field=smart_selects.db_fields.ChainedForeignKey(chained_field='target',
                                                            chained_model_field='target__zone__region',
                                                            on_delete=django.db.models.deletion.CASCADE,
                                                            to='cloudlaunch.Image'),
        ),
        migrations.RunPython(copy_cloud_image_data),
        migrations.AlterField(
            model_name='image',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    to='djcloudbridge.Region'),
        ),
        migrations.DeleteModel(
            name='CloudImage',
        ),
    ]