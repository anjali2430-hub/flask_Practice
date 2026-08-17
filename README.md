# Flask Student Registration App — CI/CD Pipeline

A Python Flask web application for managing student records with MongoDB, deployed automatically via a CI/CD pipeline using GitHub Actions to Amazon EC2.

---

## Architecture Overview

```
Developer push to main
        │
        ▼
┌─────────────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│ GitHub Actions  │ --> │  pytest  │ --> │ Docker Build│ --> │  Push to ECR │
│   (trigger)     │     │  (gate)  │     │  (SHA tag)  │     │              │
└─────────────────┘     └──────────┘     └─────────────┘     └──────┬───────┘
                                                                      │
                                                                      ▼
                                                          ┌───────────────────────┐
                                                          │    Deploy to EC2      │
                                                          │  - docker pull (ECR)  │
                                                          │  - stop old container │
                                                          │  - run new container  │
                                                          │  - curl /health gate  │
                                                          └───────────┬───────────┘
                                                                      │
                                                                      ▼
                                                          ┌───────────────────────┐
                                                          │   Email Notification  │
                                                          │  success or failure   │
                                                          │  with build details   │
                                                          └───────────────────────┘
```

---

## Tech Stack

- **App**: Python Flask + MongoDB (Atlas)
- **Testing**: pytest
- **Containerization**: Docker
- **Registry**: Amazon ECR
- **Compute**: Amazon EC2 (Ubuntu 26.04)
- **CI/CD**: GitHub Actions
- **Notifications**: Gmail SMTP

---

## Prerequisites

### AWS Resources (set up manually before pipeline runs)

| Resource | Details |
|---|---|
| ECR Repository | `flask-student-app` in `ap-south-1` |
| EC2 Instance | Ubuntu 26.04, t2.micro |
| EC2 IAM Role | `ec2_ecr_role` with `AmazonEC2ContainerRegistryReadOnly` |
| Security Group | Inbound: port 22 (SSH), port 5000 (Flask app) |
| Docker | Installed and running on EC2 |
| AWS CLI | Installed on EC2 (`/usr/bin/aws`) |

### MongoDB
- MongoDB Atlas free tier (M0 cluster)
- Database user with `atlasAdmin` role
- Network access: `0.0.0.0/0` (allow from anywhere)

### IAM User (for GitHub Actions)
- User: `anjali3112`
- Permissions: `AmazonEC2ContainerRegistryFullAccess`, `AmazonEC2ReadOnlyAccess`

---

## Repository Structure

```
flask_Practice/
├── app.py                        # Flask app with /health endpoint
├── test_app.py                   # pytest test suite
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build instructions
├── .dockerignore                 # Files excluded from Docker image
├── .env.example                  # Environment variable template
├── .github/
│   └── workflows/
│       └── ci-cd.yml             # GitHub Actions pipeline definition
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── add_student.html
│   └── update_student.html
└── README.md
```

---

## Pipeline Stages

The pipeline triggers automatically on every push to the `main` branch.

| Stage | Description |
|---|---|
| 1. Checkout | Pull latest source code |
| 2. Install dependencies | `pip install -r requirements.txt` |
| 3. Test | Run pytest suite — pipeline stops here if any test fails |
| 4. Build | Build Docker image tagged with Git commit SHA |
| 5. Push to ECR | Authenticate and push tagged image to Amazon ECR |
| 6. Deploy to EC2 | SSH into EC2, pull image, replace running container |
| 7. Health check | `curl /health` — real deploy-verification gate |
| 8. Notify | Send customized success or failure email |

---

## Required GitHub Secrets

Configure these in **Settings → Secrets and variables → Actions**:

| Secret Name | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_REGION` | `ap-south-1` |
| `ECR_REGISTRY` | `970852255916.dkr.ecr.ap-south-1.amazonaws.com` |
| `ECR_REPOSITORY` | `flask-student-app` |
| `EC2_HOST` | EC2 public IPv4 address |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Full contents of the `.pem` private key file |
| `MONGO_URI` | MongoDB Atlas connection string |
| `EMAIL_SENDER` | Gmail address used to send notifications |
| `EMAIL_PASSWORD` | Gmail App Password (16-character, not regular password) |
| `EMAIL_RECEIVER` | Email address to receive notifications |

---

## Deploy Method — SSH

The pipeline connects to EC2 using **SSH with a private key** stored in GitHub Secrets (`EC2_SSH_KEY`).

**Why SSH over SSM?**
- No additional AWS agent setup required on EC2
- Works immediately with standard Ubuntu AMIs
- Private key is stored securely in GitHub Secrets, never committed to the repo
- Simple and transparent — the exact commands run on EC2 are visible in the pipeline logs

**Deploy sequence on EC2:**
```bash
# 1. Authenticate to ECR using attached IAM role
/usr/bin/aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin <ECR_REGISTRY>

# 2. Pull the new image
docker pull <ECR_REGISTRY>/flask-student-app:<COMMIT_SHA>

# 3. Stop and remove the old container
docker stop flask-app && docker rm flask-app

# 4. Run the new container
docker run -d --name flask-app --restart unless-stopped -p 5000:5000 <image>

# 5. Verify deployment
curl http://localhost:5000/health  # must return 200
```

---

## Health Check Endpoint

The `/health` endpoint is the deploy-verification gate:

```
GET /health
```

**Success response (200):**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**Failure response (503):**
```json
{
  "status": "unhealthy",
  "database": "unreachable",
  "error": "..."
}
```

A container that starts but returns 503 is treated as a failed deployment.

---

## Email Notifications

Emails are sent via Gmail SMTP using the `dawidd6/action-send-mail` action.
Credentials are stored in GitHub Secrets — never hardcoded in the pipeline file.

**Success email includes:**
- Git commit SHA and branch
- Docker image tag pushed to ECR
- EC2 instance target
- Link to the pipeline run

**Failure email includes:**
- Which stage failed (Test / Build / Push / Deploy)
- Git commit SHA and branch
- Direct link to pipeline logs

---

## How to Reproduce a Deployment Manually

If the pipeline is unavailable, deploy manually:

```bash
# 1. SSH into EC2
ssh -i flask-app-key.pem ubuntu@<EC2_PUBLIC_IP>

# 2. Authenticate to ECR
/usr/bin/aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  970852255916.dkr.ecr.ap-south-1.amazonaws.com

# 3. Pull the image
docker pull 970852255916.dkr.ecr.ap-south-1.amazonaws.com/flask-student-app:<COMMIT_SHA>

# 4. Stop old container
docker stop flask-app && docker rm flask-app

# 5. Run new container
docker run -d \
  --name flask-app \
  --restart unless-stopped \
  -p 5000:5000 \
  -e MONGO_URI="<your-atlas-uri>" \
  970852255916.dkr.ecr.ap-south-1.amazonaws.com/flask-student-app:<COMMIT_SHA>

# 6. Verify
curl http://localhost:5000/health
```

---

## Running Tests Locally

```bash
pip install -r requirements.txt
pytest test_app.py -v
```

---

## Live Application

- **App**: `http://<EC2_PUBLIC_IP>:5000`
- **Health check**: `http://<EC2_PUBLIC_IP>:5000/health`
