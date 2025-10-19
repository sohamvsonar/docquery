# DocQuery Deployment Guide
## Frontend (Vercel) + Backend (EC2) Setup

This guide will help you deploy:
- **Frontend**: Next.js on Vercel at `docquery.me` and `www.docquery.me`
- **Backend**: FastAPI on AWS EC2 at `api.docquery.me`

**Total Setup Time**: ~45 minutes
**Monthly Cost**: ~$70-85 (EC2 ~$60 + Vercel Free)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  docquery.me (Frontend)                         │
│  ├── Vercel Edge Network (Global CDN)          │
│  ├── Next.js 15 SSR                            │
│  └── Automatic HTTPS                           │
│                                                 │
└────────────────┬────────────────────────────────┘
                 │
                 │ HTTPS API Calls
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  api.docquery.me (Backend)                      │
│  ├── AWS EC2 (t3.large)                        │
│  ├── Docker Compose:                           │
│  │   ├── FastAPI (port 8000)                   │
│  │   ├── PostgreSQL                            │
│  │   ├── Redis                                 │
│  │   └── Celery Worker                         │
│  ├── Nginx (Reverse Proxy)                     │
│  └── Let's Encrypt SSL                         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Part 1: Deploy Backend to AWS EC2

### Step 1: Launch EC2 Instance (10 min)

1. **Go to AWS Console**: https://console.aws.amazon.com/ec2

2. **Click "Launch Instance"**

3. **Configure**:
   ```
   Name: docquery-backend
   AMI: Ubuntu Server 22.04 LTS (64-bit x86)
   Instance Type: t3.large (2 vCPU, 8 GB RAM)

   Key Pair: Create new
   - Name: docquery-key
   - Type: RSA
   - Format: .pem
   - DOWNLOAD AND SAVE SECURELY

   Network:
   - Auto-assign public IP: Enable

   Security Group: Create new
   - Name: docquery-backend-sg
   - Rules:
     ✅ SSH (22) from My IP
     ✅ HTTP (80) from 0.0.0.0/0
     ✅ HTTPS (443) from 0.0.0.0/0

   Storage:
   - Root: 30 GB gp3
   - Add volume: 100 GB gp3
   ```

4. **Launch** and note the **Public IPv4 address**

---

### Step 2: Setup Domain DNS (5 min)

1. **Go to your domain registrar** (where you bought docquery.me)

2. **Add A Records**:
   ```
   Type: A | Name: api       | Value: <EC2_PUBLIC_IP> | TTL: 300
   Type: A | Name: @         | Value: 76.76.21.21     | TTL: 300  (Vercel)
   Type: A | Name: www       | Value: 76.76.21.21     | TTL: 300  (Vercel)
   ```

   **Note**: Vercel IP will be configured later, use placeholder for now

3. **Verify DNS** (wait 5-10 minutes):
   ```bash
   nslookup api.docquery.me
   # Should return your EC2 IP
   ```

---

### Step 3: Connect and Setup EC2 (15 min)

**Connect to EC2**:
```bash
# Windows (PowerShell or Git Bash)
ssh -i docquery-key.pem ubuntu@<EC2_PUBLIC_IP>

# If permission denied
chmod 400 docquery-key.pem
ssh -i docquery-key.pem ubuntu@<EC2_PUBLIC_IP>
```

**Run setup script**:
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx and Certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx git

# Verify installations
docker --version
docker-compose --version
nginx -v

# Log out and back in for docker group
exit
ssh -i docquery-key.pem ubuntu@<EC2_PUBLIC_IP>
```

**Setup storage**:
```bash
# Check disks
lsblk
# You should see nvme1n1 (100GB volume)

# Format and mount
sudo mkfs.ext4 /dev/nvme1n1
sudo mkdir -p /mnt/docquery-data
sudo mount /dev/nvme1n1 /mnt/docquery-data

# Auto-mount on reboot
UUID=$(sudo blkid -s UUID -o value /dev/nvme1n1)
echo "UUID=$UUID /mnt/docquery-data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Set ownership
sudo chown -R ubuntu:ubuntu /mnt/docquery-data

# Verify
df -h /mnt/docquery-data
```

---

### Step 4: Deploy Backend Code (10 min)

**Clone repository**:
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/docquery.git
cd docquery
```

**Configure backend environment**:
```bash
cd backend
cp .env.example .env
nano .env
```

**Edit `.env` file**:
```bash
# Generate secure values first:
# openssl rand -base64 32  (for passwords)
# openssl rand -base64 48  (for JWT secret)

# Database
POSTGRES_USER=docquery_user
POSTGRES_PASSWORD=YOUR_GENERATED_PASSWORD_HERE
POSTGRES_DB=docquery
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://docquery_user:YOUR_GENERATED_PASSWORD_HERE@postgres:5432/docquery

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=YOUR_GENERATED_JWT_SECRET_HERE
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI
OPENAI_API_KEY=sk-your-actual-openai-api-key

# App
APP_NAME=DocQuery
APP_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false

# Uploads
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=52428800

# Rate Limiting
LOGIN_RATE_LIMIT=5
```

**Save**: Ctrl+O, Enter, Ctrl+X

**Update docker-compose.yml volumes**:
```bash
cd ~/docquery
nano docker-compose.yml
```

**Change volumes to use persistent storage**:
```yaml
# Find and replace these volume paths:
# Line ~13: postgres_data:/var/lib/postgresql/data
# TO: /mnt/docquery-data/postgres:/var/lib/postgresql/data

# Line ~29: redis_data:/data
# TO: /mnt/docquery-data/redis:/data

# Line ~47: ./backend/uploads:/app/uploads
# TO: /mnt/docquery-data/uploads:/app/uploads

# Line ~75: ./backend/uploads:/app/uploads
# TO: /mnt/docquery-data/uploads:/app/uploads
```

**Start services**:
```bash
cd ~/docquery

# Build and start
docker compose up -d --build

# Watch logs (Ctrl+C to exit)
docker compose logs -f

# Wait for "Application startup complete"
```

**Create admin user**:
```bash
docker compose exec backend python scripts/create_admin.py

# Enter:
# Username: admin
# Email: admin@docquery.me
# Password: <your-secure-password>
```

**Test backend**:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","database":"connected","redis":"connected"}
```

---

### Step 5: Setup Nginx & SSL (10 min)

**Configure Nginx**:
```bash
sudo nano /etc/nginx/sites-available/docquery-backend
```

**Paste configuration**:
```nginx
server {
    listen 80;
    server_name api.docquery.me;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

**Enable site**:
```bash
sudo ln -s /etc/nginx/sites-available/docquery-backend /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

**Get SSL certificate**:
```bash
sudo certbot --nginx -d api.docquery.me

# Follow prompts:
# Email: your-email@example.com
# Agree to ToS: Yes
# Redirect HTTP to HTTPS: Yes

# Test auto-renewal
sudo certbot renew --dry-run
```

**Test HTTPS**:
```bash
curl https://api.docquery.me/health
# Should return: {"status":"healthy",...}
```

✅ **Backend is now live at https://api.docquery.me** 🎉

---

## Part 2: Deploy Frontend to Vercel

### Step 6: Prepare Frontend for Vercel (5 min)

**Update environment variable**:
```bash
# On your LOCAL machine (not EC2)
cd e:\Projects\docquery\frontend
```

Create `.env.production`:
```bash
NEXT_PUBLIC_API_URL=https://api.docquery.me
NEXT_PUBLIC_APP_NAME=DocQuery
NEXT_PUBLIC_APP_DESCRIPTION=Intelligent Document Search & RAG System
```

**Update `next.config.ts`** (if needed):
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone', // Add this for better Vercel deployment
};

export default nextConfig;
```

**Commit changes**:
```bash
git add frontend/.env.production
git add frontend/next.config.ts
git commit -m "Configure frontend for production deployment"
git push origin main
```

---

### Step 7: Deploy to Vercel (10 min)

1. **Go to Vercel**: https://vercel.com/signup

2. **Sign up/Login** with GitHub

3. **Import Project**:
   - Click "Add New" → "Project"
   - Import your `docquery` repository
   - Click "Import"

4. **Configure Project**:
   ```
   Framework Preset: Next.js
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   ```

5. **Environment Variables**:
   ```
   Name: NEXT_PUBLIC_API_URL
   Value: https://api.docquery.me

   Name: NEXT_PUBLIC_APP_NAME
   Value: DocQuery

   Name: NEXT_PUBLIC_APP_DESCRIPTION
   Value: Intelligent Document Search & RAG System
   ```

6. **Click "Deploy"** (takes 2-3 minutes)

7. **Get Vercel URL**:
   - After deployment, you'll get: `https://docquery-xxx.vercel.app`
   - Test it! The app should load but API calls will work now.

---

### Step 8: Configure Custom Domain (5 min)

**In Vercel Dashboard**:

1. **Go to**: Project Settings → Domains

2. **Add Domain**: `docquery.me`
   - Click "Add"
   - Vercel will show DNS records needed

3. **Add Domain**: `www.docquery.me`
   - Click "Add"

4. **Copy the DNS records** shown by Vercel

**In your Domain Registrar**:

1. **Update A Records** (replace the placeholder):
   ```
   Type: A | Name: @   | Value: <VERCEL_IP_FROM_DASHBOARD>
   Type: A | Name: www | Value: <VERCEL_IP_FROM_DASHBOARD>
   ```

2. **Or use CNAME** (recommended):
   ```
   Type: CNAME | Name: www | Value: cname.vercel-dns.com
   ```

3. **Wait 5-10 minutes** for DNS propagation

**Verify in Vercel**:
- Domains should show "Valid Configuration" with SSL 🔒

✅ **Frontend is now live at https://docquery.me** 🎉

---

## Part 3: Configure CORS (Important!)

**On EC2**, update backend CORS settings:

```bash
ssh -i docquery-key.pem ubuntu@<EC2_IP>
cd ~/docquery/backend
nano app/main.py
```

**Find the CORS middleware section** and update:
```python
# Find this section in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://docquery.me",
        "https://www.docquery.me",
        "https://*.vercel.app",  # For preview deployments
        "http://localhost:3000",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Restart backend**:
```bash
docker compose restart backend
```

---

## Testing Your Deployment

### Test Backend:
```bash
# Health check
curl https://api.docquery.me/health

# API docs
open https://api.docquery.me/docs
```

### Test Frontend:
1. Visit: https://docquery.me
2. Login with admin credentials
3. Upload a test document
4. Wait for processing (check EC2: `docker compose logs celery_worker`)
5. Search for content
6. Use chat/RAG feature

---

## Automated Backups (Recommended)

**On EC2**, setup daily database backups:

```bash
mkdir -p ~/backups
nano ~/backups/backup.sh
```

**Script**:
```bash
#!/bin/bash
BACKUP_DIR="/mnt/docquery-data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker compose -f /home/ubuntu/docquery/docker-compose.yml exec -T postgres \
    pg_dump -U docquery_user docquery | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

**Schedule**:
```bash
chmod +x ~/backups/backup.sh
crontab -e

# Add this line (daily at 2 AM):
0 2 * * * /home/ubuntu/backups/backup.sh
```

---

## Deploying Updates

### Frontend (Automatic):
```bash
# On your local machine
cd e:\Projects\docquery\frontend
# Make changes...
git add .
git commit -m "Update frontend"
git push origin main

# Vercel auto-deploys in ~2 minutes!
```

### Backend (Manual):
```bash
# SSH to EC2
ssh -i docquery-key.pem ubuntu@<EC2_IP>

cd ~/docquery
git pull origin main
docker compose down
docker compose up -d --build
docker compose logs -f
```

---

## Monitoring & Logs

### Backend Logs:
```bash
# SSH to EC2
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f postgres
```

### Frontend Logs:
- Go to Vercel Dashboard → Your Project → Deployments
- Click on any deployment → View Logs

---

## Cost Breakdown

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **AWS EC2** | t3.large (8GB RAM) | ~$60 |
| **EBS Storage** | 130 GB | ~$13 |
| **Data Transfer** | ~50 GB/month | ~$5 |
| **Vercel** | Hobby Plan | **Free** |
| **Domain** | .me domain | ~$10/year |
| **Total** | | **~$78-85/month** |

**Plus**: OpenAI API usage (~$10-50/month depending on usage)

---

## Security Checklist

- ✅ SSL/HTTPS on both frontend and backend
- ✅ EC2 Security Group allows only necessary ports
- ✅ Database not exposed to internet
- ✅ Strong passwords for PostgreSQL and JWT
- ✅ CORS configured for production domains only
- ✅ DEBUG=false in production
- ✅ Regular automated backups

---

## Troubleshooting

### Frontend can't connect to backend:
1. Check CORS settings in `backend/app/main.py`
2. Verify `NEXT_PUBLIC_API_URL=https://api.docquery.me` in Vercel environment variables
3. Check backend is running: `curl https://api.docquery.me/health`

### SSL certificate errors:
```bash
# On EC2
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Backend not responding:
```bash
# On EC2
docker compose ps
docker compose restart backend
docker compose logs backend
```

### Database connection errors:
```bash
# On EC2
docker compose logs postgres
docker compose restart postgres
```

---

## Quick Reference

**SSH to EC2**:
```bash
ssh -i docquery-key.pem ubuntu@<EC2_IP>
```

**View backend logs**:
```bash
docker compose logs -f backend
```

**Restart services**:
```bash
docker compose restart
```

**Rebuild and restart**:
```bash
docker compose down && docker compose up -d --build
```

---

## Next Steps

After successful deployment:

1. **Test all features** thoroughly
2. **Setup monitoring** (optional): CloudWatch for EC2, Vercel Analytics
3. **Configure error tracking** (optional): Sentry
4. **Setup staging environment** (optional): Use Vercel preview deployments
5. **Document API** for your users at https://api.docquery.me/docs

---

**Deployment Complete!** 🚀

- Frontend: https://docquery.me
- Backend: https://api.docquery.me
- API Docs: https://api.docquery.me/docs

Your DocQuery application is now live and ready for users!
