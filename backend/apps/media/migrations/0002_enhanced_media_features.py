"""
Enhanced media models migration - adds new fields to existing models
"""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('media', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        # Add new fields to MediaFile
        migrations.AddField(
            model_name='mediafile',
            name='alt_text',
            field=models.CharField(blank=True, help_text='Alt text for accessibility', max_length=500),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='download_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='last_accessed',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='folder',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='files', to='media.mediafolder'),
        ),
        
        # Enhance MediaFolder
        migrations.AddField(
            model_name='mediafolder',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='mediafolder',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subfolders', to='media.mediafolder'),
        ),
        
        # Create MediaUploadBatch model
        migrations.CreateModel(
            name='MediaUploadBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('total_files', models.PositiveIntegerField()),
                ('successful_uploads', models.PositiveIntegerField(default=0)),
                ('failed_uploads', models.PositiveIntegerField(default=0)),
                ('total_size', models.PositiveBigIntegerField(default=0)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='upload_batches', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='mediafolder',
            index=models.Index(fields=['user', 'parent'], name='media_folders_user_parent_idx'),
        ),
        migrations.AddIndex(
            model_name='mediafolder',
            index=models.Index(fields=['user', 'name'], name='media_folders_user_name_idx'),
        ),
        migrations.AddIndex(
            model_name='mediafile',
            index=models.Index(fields=['user', 'folder'], name='media_files_user_folder_idx'),
        ),
        migrations.AddIndex(
            model_name='mediauploadbatch',
            index=models.Index(fields=['user', 'status'], name='media_batches_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='mediauploadbatch',
            index=models.Index(fields=['user', '-created_at'], name='media_batches_user_created_idx'),
        ),
    ]