import json
import boto3
import requests
import os
import argparse
import uuid
from urllib.parse import urlparse

def get_filename_from_url(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

def load_data(bucket_name, cloudfront_domain):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') # Update region if needed
    s3 = boto3.client('s3', region_name='us-east-1')
    music_table = dynamodb.Table('Music')

    with open('2026a2_songs.json', 'r') as file:
        data = json.load(file)

    os.makedirs('temp_images', exist_ok=True)

    print(f"Starting pipeline for {len(data['songs'])} songs...")

    for song in data['songs']:
        song_id = str(uuid.uuid4())
        title = song['title']
        artist = song['artist']
        year = song['year']
        album = song.get('album', 'Unknown Album')
        img_url_original = song['img_url']

        filename = get_filename_from_url(img_url_original)
        local_path = f"temp_images/{filename}"

        # 1. Download image locally if we haven't already
        if not os.path.exists(local_path):
            try:
                print(f"Downloading {filename}...")
                response = requests.get(img_url_original)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                print(f"Error downloading {img_url_original}: {e}")
                continue

        # 2. Upload to S3 if a bucket is provided
        new_img_url = img_url_original # Default to original if no S3
        if bucket_name and cloudfront_domain:
            s3_key = f"images/{filename}"
            try:
                s3.upload_file(local_path, bucket_name, s3_key)
                new_img_url = f"https://{cloudfront_domain}/{s3_key}"
            except Exception as e:
                print(f"Error uploading {filename} to S3: {e}")
                continue

        # 3. Insert into DynamoDB
        try:
            music_table.put_item(
                Item={
                    'id': song_id,
                    'title': title,
                    'artist': artist,
                    'year': year,
                    'album': album,
                    'img_url': new_img_url
                }
            )
            print(f"Inserted to DynamoDB: {title} by {artist}")
        except Exception as e:
            print(f"Error inserting into DynamoDB: {e}")

    print("✅ Data loading complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load data into DynamoDB and S3')
    parser.add_argument('--bucket', required=False, help='Your S3 bucket name (optional for now)')
    parser.add_argument('--cloudfront', required=False, help='Your CloudFront domain (optional for now)')
    args = parser.parse_args()

    load_data(args.bucket, args.cloudfront)
