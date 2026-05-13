# Lossless - Serverless Music Subscription Cloud Application

This repository contains the full source code for the Music Subscription Cloud Application, completed per the requirements of "AWS Assignment 2". It implements a decoupled, modern cloud architecture with a Serverless backend and a globally distributed Serverless frontend.

## Architecture Chosen: Serverless (API Gateway + Lambda)

This architecture utilizes purely serverless technology components that allow for infinite horizontal scaling and near-zero costs while in an idle state (pay-for-what-you-use).

- **Data Tier:** Amazon DynamoDB (`music`, `login`, `user_subscriptions` tables).
- **Storage & CDN:** Amazon S3 (Origin) + Amazon CloudFront (CDN cache with OAC) for both the high-resolution album arts and the frontend Web GUI.
- **Compute:** AWS Lambda running Python 3.11 with `mangum` wrapping a Flask API.
- **API Tier:** Amazon API Gateway providing secure ingress.
- **Identity:** Standard AWS IAM (using the `LabRole` for student environments).

## Project Structure

```
AWS_Assignment_2/
├── 2026a2_songs.json      # Dataset
├── project_roadmap.md     # Specifications
├── template.yaml          # AWS SAM configuration
├── src/
│   ├── app.py             # Flask application (API logic)
│   ├── init_tables.py     # Script to construct the DynamoDB schema
│   ├── lambda_handler.py  # Mangum handler bridging Lambda/FastAPI
│   ├── load_data.py       # Script pushing S3 media and Dynamo records
│   └── requirements.txt   # Backend dependencies
└── frontend/
    ├── index.html         # User Interface
    ├── style.css          # Glassmorphism dark-mode styles
    └── app.js             # Logic for authentication and query API calls
```

## Step-by-Step Deployment Guide

### Phase 1: Storage and Databases
1. Ensure your terminal is authenticated with your AWS Learner Lab Credentials.
2. Open a local terminal in this repository.
3. **Initialize the Tables:**
   ```bash
   pip install boto3
   python src/init_tables.py
   ```
   Wait until all 3 tables (`music`, `login`, `user_subscriptions`) report as "ACTIVE".
4. **Setup S3 and CloudFront:**
   - Create a new S3 bucket (e.g. `your-lossless-bucket-name`).
   - Block all public access for security.
   - Create a CloudFront Distribution pointing to that S3 Bucket.
   - Use **OAC (Origin Access Control)** to grant CloudFront permissions to read from S3.
5. **Populate Dataset (The Pipeline):**
   ```bash
   pip install requests
   python src/load_data.py --bucket your-lossless-bucket-name --cloudfront d123456abcdef.cloudfront.net
   ```
   This downloads images, uploads them to your bucket, sets CloudFront URLs, and indexes everything losslessly in DynamoDB.

### Phase 2: Deploy Serverless Backend (AWS SAM)
1. Install AWS SAM CLI if you haven't yet.
2. Build the application dependencies:
   ```bash
   sam build
   ```
3. Deploy the application:
   ```bash
   sam deploy --guided
   ```
   Provide a Stack Name (e.g., `Lossless-Backend`). Accept the defaults and ensure `LabRole` is valid in your account.
4. After SAM finishes, it will output a `MusicApi` URL (e.g., `https://xyz.execute-api.us-east-1.amazonaws.com/Prod/api/`). Use this URL for Step 3.

### Phase 3: Deploy Frontend
1. Open `frontend/app.js` and locate `const API_BASE_URL = 'http://localhost:5000/api';`.
2. Change the URL to your API Gateway `Prod` URL from the previous step. Save the file.
3. Upload `index.html`, `style.css`, and `app.js` to your S3 bucket root.
4. Set `index.html` as the default root object in your CloudFront distribution settings.
5. Invalidate your CloudFront cache if necessary.
6. Navigate to your CloudFront URL in your browser and enjoy your incredibly fast, infinitely scalable Music Application!
