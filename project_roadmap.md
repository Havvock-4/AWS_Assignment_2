# Project Roadmap: Music Subscription Cloud Application

## 1. Database & Storage Initialization

These scripts handle the "Lossless" data migration and infrastructure setup.

### A. DynamoDB Table Creator (`init_tables.py`)

This script implements the required LSI and GSI based on the cardinality of `2026a2_songs.json`.

- **Partition Key (PK):** `artist` — High cardinality, good for distribution.
- **Sort Key (SK):** `title` — Ensures uniqueness (Lossless) as an artist rarely has two songs with the identical name.
- **LSI (ArtistYearIndex):** Allows searching all songs by an artist filtered by a specific year.
- **GSI (AlbumIndex):** Allows searching for a specific album across all artists.

```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def create_music_table():
    try:
        table = dynamodb.create_table(
            TableName='music',
            KeySchema=[
                {'AttributeName': 'artist', 'KeyType': 'HASH'},
                {'AttributeName': 'title', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'artist', 'AttributeType': 'S'},
                {'AttributeName': 'title', 'AttributeType': 'S'},
                {'AttributeName': 'year', 'AttributeType': 'S'},
                {'AttributeName': 'album', 'AttributeType': 'S'}
            ],
            LocalSecondaryIndexes=[{
                'IndexName': 'ArtistYearIndex',
                'KeySchema': [
                    {'AttributeName': 'artist', 'KeyType': 'HASH'},
                    {'AttributeName': 'year', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }],
            GlobalSecondaryIndexes=[{
                'IndexName': 'AlbumIndex',
                'KeySchema': [
                    {'AttributeName': 'album', 'KeyType': 'HASH'},
                    {'AttributeName': 'title', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("Table 'music' created.")
    except Exception as e:
        print(f"Error: {e}")

# Note: Repeat similar logic for 'login' table (PK: email)
```

### B. Data Loader & Image Pipeline (`load_data.py`)

This script performs the lossless JSON import and the S3 image migration.

1. Read `2026a2_songs.json`.
2. Download images via `requests`.
3. Upload to S3 using `put_object`.
4. Update the `image_url` to point to your S3/CloudFront URL before saving to DynamoDB.

---

## 2. Web Application Requirements

### Login & Registration Logic

- **Login:** A query on the `login` table using the `email` as the Key. Compare the retrieved password with the input.
- **Register:** Use `attribute_not_exists(email)` in a `PutItem` condition to ensure uniqueness without performing a manual "check-then-write" (prevents race conditions).

### Main Page Features

**Subscription Area:** Requires a separate DynamoDB table (e.g., `user_subscriptions`) with `PK: email` and `SK: song_id`.

**Query Area:**

- If only **Artist** is provided → query the base table.
- If **Artist + Year** is provided → query the LSI.
- If **Album** is provided → query the GSI.
- If **multiple fields** (e.g., Artist + Album) → perform a query on the most restrictive index and use a `FilterExpression` for the rest.

---

## 3. The Tri-Backend Architectural Design

For the report, you must implement and justify these three approaches:

| Architecture | Deployment Strategy | Rationale for Report |
|---|---|---|
| **EC2** | Python/Flask app running on Amazon Linux 2023 via UserData scripts. | **Pros:** Maximum control over OS/Environment. **Cons:** High maintenance; not cost-effective for idle time. |
| **ECS (Fargate)** | Dockerize the Flask app. Push to ECR. Deploy as a Fargate Service. | **Pros:** Seamless scaling and environment parity. **Cons:** Complex configuration of Task Definitions and VPCs. |
| **Serverless** | API Gateway + Lambda (using `mangum` to wrap the Flask/FastAPI app). | **Pros:** Infinite scaling, zero cost when idle. **Cons:** Cold starts can impact latency. |

---

## 4. Architectural Justification (Report Ready)

### Database Key Schema Rationale

The "Lossless" requirement is met by using a **Composite Key** (`artist` + `title`). In the provided dataset, while an artist might have multiple songs in an album, the combination of Artist and Title is unique. Using `artist` as the Partition Key ensures related songs are stored in the same physical partition, making "Artist-based" queries extremely efficient.

### Frontend Hosting: S3 + CloudFront

Instead of serving static HTML from EC2, we use **S3** (Origin) + **CloudFront** (CDN).

- **Latency:** Users in Melbourne will hit the Edge Location for cached images and HTML.
- **Cost:** Significantly cheaper than keeping an EC2 instance running 24/7 just to serve CSS/JS.
- **Security:** Using Origin Access Control (OAC) ensures that the S3 bucket is not public, and only CloudFront can fetch the images.

### Preferred Architecture

**API Gateway + Lambda** is the most appropriate for this music app. Since student users only access the app during demo times, paying for 24/7 EC2 or ECS uptime is inefficient. Serverless architecture aligns with the "pay-as-you-go" cloud philosophy.

---

## 5. Security & Deployment Checklist

- [ ] **LabRole:** Ensure all service-to-service communication (Lambda to DynamoDB) uses the pre-created LabRole.
- [ ] **Standard Ports:** Ensure the EC2 Load Balancer or API Gateway is listening on Port 80/443.
- [ ] **No Beanstalk:** Ensure deployment is handled via the specific services listed (EC2/ECS/Lambda).
- [ ] **Citations:** Include inline comments for any Boto3 boilerplate or logic adapted from AWS documentation.

---

> **Next Step:** What specific part of the backend implementation would you like to dive into first — the Lambda handlers or the ECS Docker configuration?
