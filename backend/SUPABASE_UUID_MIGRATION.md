# Supabase UUID Migration Guide

## Overview

This guide explains the migration from digit-based user IDs to UUID-based user identifiers for Supabase storage organization. This change improves data security, privacy, and provides better scalability.

## What Changed

### Before (Digit ID Structure)

```markdown
supabase-bucket/
├── 1/                    # User with ID 1
│   ├── media/
│   ├── avatars/
│   └── thumbnails/
├── 2/                    # User with ID 2
│   ├── media/
│   └── posts/
```

### After (UUID Structure)

```bash
supabase-bucket/
├── 550e8400-e29b-41d4-a716-446655440000/  # User UUID
│   ├── media/
│   ├── avatars/
│   └── thumbnails/
├── 6ba7b810-9dad-11d1-80b4-00c04fd430c8/  # Another User UUID
│   ├── media/
│   └── posts/
```

## Benefits

1. **Privacy**: UUIDs don't expose user count or sequence
2. **Security**: Harder to guess other users' folders
3. **Scalability**: UUIDs work across distributed systems
4. **Consistency**: Aligns with user profile UUIDs

## Migration Process

### Step 1: Update Upload Path Functions

The upload path functions in `apps/core/upload_paths.py` have been updated to use UUIDs:

- `user_media_upload_path()` - Now uses `instance.user.profile.id`
- `user_thumbnail_upload_path()` - Now uses `instance.user.profile.id`
- `user_avatar_upload_path()` - Now uses `instance.id` (UserProfile UUID)
- `user_post_media_upload_path()` - Now uses `instance.user.profile.id`

### Step 2: Run Migration Command

```bash
# Dry run to see what would be migrated
python manage.py migrate_supabase_to_uuid --dry-run --verbose

# Migrate all users
python manage.py migrate_supabase_to_uuid --verbose

# Migrate specific user
python manage.py migrate_supabase_to_uuid --user-id 123 --verbose
```

### Step 3: Verify Migration

After migration, verify that:

1. New uploads use UUID paths
2. Existing files are accessible via new paths
3. File URLs work correctly

### Step 4: Update Supabase RLS Policies

Update your Supabase RLS policies to work with UUIDs:

```sql
-- Old policy (digit-based)
CREATE POLICY "Users can access own files" ON storage.objects
FOR ALL USING ((storage.foldername(name))[1] = auth.uid()::text);

-- New policy (UUID-based) 
CREATE POLICY "Users can access own files" ON storage.objects
FOR ALL USING (
  (storage.foldername(name))[1] IN (
    SELECT profile_id::text 
    FROM user_profiles 
    WHERE user_id = (auth.jwt() ->> 'user_id')::int
  )
);
```

### Step 5: Clean Up Old Files (Optional)

After verifying everything works:

```bash
# Dry run cleanup
python manage.py cleanup_old_supabase_folders --dry-run --verbose

# Actually delete old files (BE CAREFUL!)
python manage.py cleanup_old_supabase_folders --confirm --verbose
```

## Helper Functions

### `get_user_storage_path(user, folder="")`

Get the correct storage path for a user, with UUID fallback support.

### `find_user_file_path(user, filename, subfolders=None)`

Find a file for a user, checking both UUID and digit ID paths.

### `get_file_url_with_fallback(user, file_path)`

Get file URL with automatic fallback to legacy paths.

## Backward Compatibility

During the transition period, the system supports both structures:

1. **New uploads** use UUID paths automatically
2. **Existing files** remain accessible via helper functions
3. **File lookups** check both UUID and digit paths
4. **URLs** work for both old and new structures

## Testing

1. **Upload new files** - Should use UUID paths
2. **Access existing files** - Should work via fallback
3. **Update user profiles** - Should not break file access
4. **Delete files** - Should work for both structures

## Troubleshooting

### Files Not Found After Migration

- Check if user has a profile: `User.objects.select_related
('profile').get(id=X)`
- Verify migration completed: Check both old and new paths in Supabase
- Use helper functions: `find_user_file_path()` for debugging

### RLS Policy Issues

- Ensure policies are updated for UUID structure
- Test policy with actual UUIDs from user profiles
- Check Supabase logs for policy violations

### Performance Issues

- Index user profiles by UUID if needed
- Consider caching UUID mappings
- Monitor file lookup performance

## Rollback Plan

If needed, you can rollback by:

1. Reverting upload path functions to use `instance.user.id`
2. Updating RLS policies back to digit-based
3. Using cleanup command to remove UUID folders (if desired)

## Code Examples

### Getting User Storage Path

```python
from apps.core.uuid_transition_helpers import get_user_storage_path

# Get user's media folder path
path = get_user_storage_path(user, 'media')
# Returns: "550e8400-e29b-41d4-a716-446655440000/media"
```

### Finding Files with Fallback

```python
from apps.core.uuid_transition_helpers import find_user_file_path

# Find user's avatar
path = find_user_file_path(user, 'avatar.jpg', ['avatars'])
# Returns full path if found in either UUID or digit structure
```

### Getting URLs with Fallback

```python
from apps.core.uuid_transition_helpers import get_file_url_with_fallback

# Get file URL with automatic fallback
url = get_file_url_with_fallback(user, 'media/photo.jpg')
# Returns URL whether file is in UUID or digit folder
```

## Security Considerations

1. **UUIDs are not secret** - Don't rely on them for access control
2. **Maintain RLS policies** - Always use proper row-level security
3. **Validate user access** - Check ownership before file operations
4. **Log access attempts** - Monitor for unauthorized access patterns

## Monitoring

Monitor the following during and after migration:

- File upload success rates
- File access errors
- Storage API response times
- RLS policy violations in Supabase logs
- User profile creation for new users
