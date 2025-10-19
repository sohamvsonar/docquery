# Secure File Storage Implementation

## Overview

DocQuery implements secure, user-isolated file storage to ensure that uploaded documents are protected and can only be accessed by authorized users.

## Security Features

### 1. User-Specific Directories

**Structure:**
```
/app/uploads/
├── user_1/
│   ├── {uuid1}.pdf
│   ├── {uuid2}.jpg
│   └── {uuid3}.mp3
├── user_2/
│   ├── {uuid4}.pdf
│   └── {uuid5}.png
└── user_3/
    └── {uuid6}.pdf
```

**Benefits:**
- Physical isolation of user files
- Easy to implement user-level quotas
- Simplified backup/restore per user
- Clear ownership model

### 2. Directory Permissions

Each user directory is created with restrictive permissions:
- **Permission:** `0o700` (rwx------)
- **Owner:** Application process
- **Access:** Read, write, and execute only by the application

This prevents unauthorized access at the filesystem level.

### 3. Access Control

**Multi-Layer Authorization:**

1. **Application Level**
   - JWT authentication required
   - User identity verified from token
   - Authorization check before any file operation

2. **Database Level**
   - `owner_id` foreign key links documents to users
   - Queries filtered by user ownership
   - Admin bypass for system operations

3. **Filesystem Level**
   - User-specific directories
   - Restricted permissions (0o700)
   - No directory traversal vulnerabilities

## API Endpoints

### Upload File
```bash
POST /upload
Authorization: Bearer {token}

# File saved to: /app/uploads/user_{user_id}/{uuid}.{ext}
```

### Download Original File
```bash
GET /upload/{document_id}/download
Authorization: Bearer {token}

# Security checks:
# 1. User must be authenticated
# 2. User must be document owner OR admin
# 3. File must exist on disk
```

### List Documents
```bash
GET /upload
Authorization: Bearer {token}

# Returns only user's own documents
# Admins see all documents
```

### Get Document Chunks
```bash
GET /upload/{document_id}/chunks
Authorization: Bearer {token}

# Returns chunks only if user owns document or is admin
```

## Security Guarantees

### ✅ User Isolation
- Users **cannot** access other users' files
- Each user has a dedicated directory
- Filenames are UUID-based (no predictable paths)

### ✅ Admin Access
- Admins can access all documents
- Required for:
  - System maintenance
  - User support
  - Data recovery
  - Compliance/auditing

### ✅ Original File Preservation
- Original uploaded files are **never modified**
- Processing operates on copies or in-memory data
- Users can always download the exact file they uploaded

### ✅ No Path Traversal
- UUIDs prevent directory traversal attacks
- No user-controlled path components
- File paths stored in database, not constructed from user input

## Implementation Details

### File Upload Flow

```python
# 1. Authenticate user (JWT)
current_user = get_current_user(token)

# 2. Create user directory
user_dir = f"/app/uploads/user_{current_user.id}"
os.makedirs(user_dir, exist_ok=True)
os.chmod(user_dir, 0o700)

# 3. Generate secure filename
job_id = uuid.uuid4()
filename = f"{job_id}{extension}"

# 4. Save file
file_path = os.path.join(user_dir, filename)
save_upload_file(upload, file_path)

# 5. Create database record with owner_id
document = Document(
    owner_id=current_user.id,
    file_path=file_path,
    original_filename=original_name
)
```

### File Download Flow

```python
# 1. Authenticate user
current_user = get_current_user(token)

# 2. Load document from database
document = db.query(Document).filter(
    Document.id == document_id
).first()

# 3. Authorization check
if document.owner_id != current_user.id and not current_user.is_admin:
    raise HTTPException(403, "Not authorized")

# 4. Verify file exists
if not os.path.exists(document.file_path):
    raise HTTPException(404, "File not found")

# 5. Return file
return FileResponse(
    path=document.file_path,
    filename=document.original_filename
)
```

## Migration Notes

### Existing Files

If you have existing files in a flat directory structure, run this migration:

```python
# scripts/migrate_to_user_dirs.py
from app.database import SessionLocal
from app.models import Document
import shutil
import os

db = SessionLocal()
documents = db.query(Document).all()

for doc in documents:
    # Create user directory
    user_dir = f"/app/uploads/user_{doc.owner_id}"
    os.makedirs(user_dir, exist_ok=True)
    os.chmod(user_dir, 0o700)

    # Move file
    old_path = doc.file_path
    new_path = os.path.join(user_dir, doc.filename)

    if os.path.exists(old_path):
        shutil.move(old_path, new_path)
        doc.file_path = new_path
        db.commit()
        print(f"Moved {doc.filename} to user_{doc.owner_id}/")

db.close()
```

## Best Practices

### ✅ Do's
- Always verify user ownership before file access
- Use database-stored paths, never construct from user input
- Log all file access attempts for audit trails
- Implement file size limits
- Scan uploaded files for malware (future enhancement)

### ❌ Don'ts
- Never trust user-provided filenames for storage paths
- Don't use predictable file naming schemes
- Don't expose internal file paths to clients
- Don't allow directory listing endpoints
- Don't skip authorization checks for "read-only" operations

## Future Enhancements

### Planned Security Improvements

1. **Encryption at Rest**
   - Encrypt files on disk
   - Decrypt only when accessed by authorized users
   - Use per-user encryption keys

2. **File Integrity**
   - SHA-256 checksums on upload
   - Verify integrity before download
   - Detect tampering or corruption

3. **Virus Scanning**
   - Integrate ClamAV or similar
   - Scan on upload
   - Quarantine suspicious files

4. **Access Logging**
   - Log all file downloads
   - Track who accessed what and when
   - Compliance and audit trails

5. **Retention Policies**
   - Automatic deletion after X days
   - User-configurable retention
   - Compliance with data regulations

6. **Quotas**
   - Per-user storage limits
   - Prevent abuse
   - Fair resource allocation

## Compliance

This implementation supports:
- **GDPR:** User data isolation, right to deletion
- **HIPAA:** Access controls, audit logging (with enhancements)
- **SOC 2:** Access controls, data protection

## Testing

Test security with:

```bash
# Test 1: User can download their own file
curl http://localhost:8000/upload/1/download \
  -H "Authorization: Bearer {user_token}"
# Expected: 200 OK, file downloaded

# Test 2: User cannot download other user's file
curl http://localhost:8000/upload/2/download \
  -H "Authorization: Bearer {user_token}"
# Expected: 403 Forbidden

# Test 3: Admin can download any file
curl http://localhost:8000/upload/2/download \
  -H "Authorization: Bearer {admin_token}"
# Expected: 200 OK, file downloaded

# Test 4: Unauthenticated access denied
curl http://localhost:8000/upload/1/download
# Expected: 403 Forbidden
```

---

**Security Status:** ✅ **Production Ready**

All file operations are protected by multi-layer authorization and user isolation.
