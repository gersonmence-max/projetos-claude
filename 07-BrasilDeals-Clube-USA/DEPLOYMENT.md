# BrasilDeals VPS Deployment Guide

Complete step-by-step guide to deploy BrasilDeals on a production VPS and make it generate real revenue.

## Overview

Expected setup time: **30-45 minutes**
Monthly cost: **$5-40**
Potential revenue: **$500-5000+/month**

## Prerequisites Checklist

Before starting, you need:

- [ ] A VPS provider (DigitalOcean, AWS, Linode, Hetzner)
- [ ] Telegram Bot Token (from @BotFather)
- [ ] Twilio Account (WhatsApp Sandbox setup)
- [ ] Amazon Associates Account
- [ ] Amazon PA-API credentials
- [ ] PostgreSQL database (or Supabase account)

## Step 1: Provision VPS

### Option A: DigitalOcean (Recommended for beginners)

1. Go to https://www.digitalocean.com
2. Click "Create" → "Droplets"
3. Select:
   - Ubuntu 22.04 (LTS)
   - Basic: $6/month (2GB RAM, 1vCPU)
   - Datacenter: New York or Frankfurt
   - Add SSH key for authentication
4. Click "Create Droplet"
5. Wait 1-2 minutes for creation
6. Note the IP address (e.g., 192.0.2.1)

### Option B: AWS EC2

1. Go to AWS Console
2. EC2 → Instances → Launch Instance
3. Select:
   - Ubuntu Server 22.04 LTS AMI
   - t3.micro (eligible for free tier, or t3.small for $10/month)
   - Default VPC and settings
   - Security Group: Open ports 22, 80, 443
4. Click "Launch"
5. Create/select SSH key pair and download
6. Note the public IP

### Option C: Other Providers (Linode, Hetzner)

Similar steps - just need Ubuntu 20.04+ with SSH access.

## Step 2: Initial Server Setup

```bash
# SSH into your server
ssh root@YOUR_VPS_IP

# Update system packages
apt update && apt upgrade -y

# Install required software
apt install -y \
  python3.10 \
  python3.10-venv \
  python3-pip \
  postgresql \
  postgresql-contrib \
  git \
  curl \
  wget \
  nano

# Create non-root user (recommended for security)
adduser brasildeals
usermod -aG sudo brasildeals
su - brasildeals
```

## Step 3: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, execute:
CREATE USER brasildeals_user WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE brasildeals OWNER brasildeals_user;
ALTER USER brasildeals_user CREATEDB;

# Exit
\q

# Test connection
psql -U brasildeals_user -d brasildeals -h localhost
```

**UPDATE .env** with:
```
DATABASE_URL=postgresql://brasildeals_user:your_secure_password_here@localhost:5432/brasildeals
```

## Step 4: Clone Project & Setup Python Environment

```bash
# Navigate to /opt
cd /opt

# Clone repository (or download/scp your code)
git clone https://github.com/yourusername/brasildeals.git
# OR download zip: wget https://github.com/yourrepo/archive/refs/heads/main.zip

cd brasildeals

# Create Python virtual environment
python3.10 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit with your credentials
nano .env
```

Fill in these critical values:

```bash
# Database (already set above)
DATABASE_URL=postgresql://brasildeals_user:password@localhost:5432/brasildeals

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIjklmnOpqrSTUvwxyzABCDef
TELEGRAM_CHANNEL_ID=-100123456789
TELEGRAM_GROUP_ID=-100987654321

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=+14155552671
WHATSAPP_RECIPIENTS=+5511987654321,+5521987654321

# Amazon
AMAZON_ACCESS_KEY=your_access_key
AMAZON_SECRET_KEY=your_secret_key
AMAZON_PARTNER_TAG=yourtag-20

# Settings
DRY_RUN=false
DEBUG=false
```

**Save**: Ctrl+O, Enter, Ctrl+X

## Step 6: Initialize Database

```bash
# Still in /opt/brasildeals with venv activated

python3 << 'PYEOF'
from database import db
db.init_db()
print("Database initialized!")
PYEOF
```

## Step 7: Test Before Going Live

```bash
# Health check
python main.py --mode health

# Should show:
# - Database: OK
# - Configuration: OK
# - Scheduler Jobs: 4 configured

# Dry run (NO real posts)
python main.py --mode dry-run

# Check logs
tail logs/brasildeals.log

# View dashboard
python main.py --mode dashboard
```

## Step 8: Setup Systemd Service (24/7 Operation)

```bash
# Copy service file
sudo cp brasildeals.service /etc/systemd/system/

# Create service user
sudo useradd -r -s /bin/bash brasildeals

# Set permissions
sudo chown -R brasildeals:brasildeals /opt/brasildeals

# Edit service file paths (if different)
sudo nano /etc/systemd/system/brasildeals.service

# Reload daemon and start service
sudo systemctl daemon-reload
sudo systemctl enable brasildeals
sudo systemctl start brasildeals

# Check status
sudo systemctl status brasildeals

# View logs
sudo journalctl -u brasildeals -f
```

## Step 9: Configure Auto-Restart & Monitoring

```bash
# Create cron job for health checks
(sudo crontab -e)

# Add this line to check every hour:
0 * * * * /opt/brasildeals/venv/bin/python /opt/brasildeals/main.py --mode health > /dev/null || sudo systemctl restart brasildeals

# Add daily backup of database:
0 2 * * * pg_dump brasildeals > /opt/brasildeals/backups/brasildeals_$(date +\%Y\%m\%d).sql
```

## Step 10: Setup Firewall & Security

```bash
# Allow SSH only
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp

# Disallow root login
sudo nano /etc/ssh/sshd_config
# Change: PermitRootLogin no

# Restart SSH
sudo systemctl restart sshd

# Check open ports
sudo netstat -tulpn
```

## Step 11: Monitor & Maintain

### Check Status Daily

```bash
# SSH into server
ssh brasildeals@YOUR_VPS_IP

# Check if service is running
sudo systemctl status brasildeals

# View recent logs
sudo journalctl -u brasildeals -n 50

# Check database
psql -U brasildeals_user -d brasildeals

# Count deals posted
SELECT COUNT(*) FROM deals WHERE posted_at > NOW() - INTERVAL '1 day';

# View revenue today
SELECT SUM(commission_amount) FROM commissions WHERE tracked_at > NOW() - INTERVAL '1 day';
```

### Backup Database Weekly

```bash
# Manual backup
pg_dump -U brasildeals_user brasildeals > brasildeals_backup.sql

# Or setup automated backups to S3
aws s3 sync /opt/brasildeals/backups s3://your-bucket/brasildeals/
```

### Update Code

```bash
cd /opt/brasildeals
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart brasildeals
```

## Step 12: Setup Error Tracking (Optional)

### Sentry for Error Monitoring

1. Create account at https://sentry.io
2. Create new project "BrasilDeals"
3. Copy DSN URL
4. Update .env:
```bash
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```
5. Restart service:
```bash
sudo systemctl restart brasildeals
```

## Step 13: Generate Revenue

### Start Monetization

1. **Existing Channels**
   - Promote to Telegram: 100+ deals/month
   - WhatsApp: Personal network

2. **Grow Audience**
   - Create public channels: @BrasilDealsUSA
   - Telegram bot for deals
   - TikTok/Instagram promotional videos

3. **Premium Features**
   - Premium tier: $5/month for early deals
   - Enterprise alerts via API

4. **Sponsorships**
   - Brands pay to feature deals
   - Newsletter sponsorships

### Expected Revenue

With moderate promotion:
- 50-100 clicks/day from posted deals
- 5-10% conversion rate
- $50 average sale
- 4% Amazon commission

**Monthly**: 50 clicks × 5 conversions × $50 × 4% = **$500/month**

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status brasildeals

# View detailed error
sudo journalctl -u brasildeals -n 100

# Check Python errors
/opt/brasildeals/venv/bin/python /opt/brasildeals/main.py --mode health

# Check permissions
sudo chown -R brasildeals:brasildeals /opt/brasildeals
```

### Database Connection Failed

```bash
# Test connection
psql -U brasildeals_user -h localhost -d brasildeals

# Check DATABASE_URL in .env
grep DATABASE_URL /opt/brasildeals/.env

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Telegram Messages Not Sending

```bash
# Check token
curl https://api.telegram.org/botYOUR_TOKEN/getMe

# Check logs
sudo journalctl -u brasildeals -f | grep -i telegram

# Test with dry-run
python main.py --mode dry-run
```

### Out of Memory

```bash
# Check memory usage
free -h
top

# Increase swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Rollback Changes

```bash
# Stop service
sudo systemctl stop brasildeals

# Revert to previous version
cd /opt/brasildeals
git revert HEAD
source venv/bin/activate
pip install -r requirements.txt

# Restore database from backup
psql -U brasildeals_user brasildeals < backup.sql

# Start service
sudo systemctl start brasildeals
```

## SSL/HTTPS (If Using Web Dashboard)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

## Next Steps

1. Monitor first week's performance
2. Adjust scrape times based on traffic
3. Add more RSS feeds if needed
4. Promote channels to grow audience
5. Monitor revenue and optimize
6. Scale to multiple channels

## Support

- **Logs**: `/opt/brasildeals/logs/brasildeals.log`
- **Database**: `psql brasildeals`
- **Status**: `systemctl status brasildeals`
- **Updates**: `git pull && systemctl restart brasildeals`

---

**Happy scraping and earning!** Generate $$$$ with BrasilDeals!
