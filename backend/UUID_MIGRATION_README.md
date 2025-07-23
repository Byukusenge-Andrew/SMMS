# UUID Migration Guide

This project has been updated to use UUID primary keys for all models. Here's how to migrate your existing database or set up a new one with these changes.

## Option 1: Rebuilding the Database (Recommended for development)

If you're fine with losing your current data or are setting up a new instance, this is the easiest approach:

1. Drop your existing database:

   ```bash
   python manage.py dbshell
   DROP DATABASE your_database_name;
   CREATE DATABASE your_database_name;
   exit
   ```

   For PostgreSQL, you might need to do:

   ```bash
   dropdb your_database_name
   createdb your_database_name
   ```

2. Run the migrations:

   ```bash
   python manage.py migrate
   ```

3. Create a new superuser:

   ```bash
   python manage.py createsuperuser
   ```

## Option 2: Running Migrations on Existing Database

If you need to preserve your data, the migrations have been set up to:

1. Add UUID fields to models that previously had integer IDs
2. Generate UUIDs for existing records
3. Replace the old integer IDs with the UUIDs

To run this process:

```bash
python manage.py migrate
```

## Model Changes

The following models now use UUID primary keys:

- UserProfile (already had UUID)
- Team (already had UUID)
- TeamMember (already had UUID)
- SocialMediaAccount
- EmailVerificationToken
- SocialSet
- Post
- AnalyticsData
- CommentAnalytics
- PerformanceReport
- BestPerformingPost
- PlatformAverage

## Important Notes

1. **Foreign Keys**: All foreign keys referencing these models have been updated to reference UUID fields.

2. **Serialization**: When serializing these models, the UUID fields will be represented as strings. Make sure your frontend can handle UUID strings.

3. **API Changes**: If you were accessing these models via API and had code expecting integer IDs, you'll need to update it to handle UUID strings.

4. **Performance**: UUIDs are slightly larger than integers, but provide the benefits of global uniqueness and better security.

5. **Database Indexes**: Primary key indexes have been maintained automatically by the database, but you may want to review other indexes if you have custom ones.

## Troubleshooting

If you encounter any issues during migration:

1. For database constraint errors, you may need to drop constraints before migrating and recreate them after.

2. If you get stuck with a partially completed migration, it's often safer to restore from backup and retry with Option 1 (rebuilding).

3. Check the migration files in each app's migrations directory if you need to understand the specific changes being made.
