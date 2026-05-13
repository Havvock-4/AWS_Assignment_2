import json
import boto3
import requests
import io
import os
import argparse
import logging
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(json_file_path, bucket_name, cloudfront_domain, region):
    """
    1. Reads 2026a2_songs.json
    2. Downloads images via requests
    3. Uploads images to S3
    4. Modifies the image_url to CloudFront domain
    5. Saves items to DynamoDB 'music' table
    """
    
    # Initialize AWS resources
    # Using specific region for S3 and DynamoDB
    s3_client = boto3.client('s3', region_name=region)
    dynamodb = boto3.resource('dynamodb', region_name=region)
    music_table = dynamodb.Table('music')

    if not os.path.exists(json_file_path):
        logger.error(f"Cannot find the file: {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    songs = data.get('songs', [])
    if not songs:
        logger.info("No songs found in the JSON file.")
        return

    logger.info(f"Loaded {len(songs)} songs from {json_file_path}. Processing...")

    for song in songs:
        title = song.get('title')
        artist = song.get('artist')
        year = song.get('year')
        album = song.get('album')
        original_img_url = song.get('img_url')

        if not original_img_url:
            logger.warning(f"Skipping {artist} - {title}: No image URL provided.")
            continue

        # Derived attributes
        # Clean artist name to be used as S3 object key prefix
        safe_artist = artist.replace(" ", "_").replace("'", "")
        safe_title = title.replace(" ", "_").replace("'", "")
        # Get image extension
        ext = original_img_url.split('.')[-1]
        if '?' in ext:
            ext = ext.split('?')[0] # handle query strings if any
            
        s3_object_key = f"images/{safe_artist}-{safe_title}.{ext}"
        
        # 2. Download Image
        logger.info(f"Downloading image for {artist} - {title} from {original_img_url} ...")
        try:
            response = requests.get(original_img_url, timeout=10)
            response.raise_for_status()
            image_data = response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image for {artist} - {title}: {e}")
            continue
            
        # 3. Upload to S3
        logger.info(f"Uploading image to S3 bucket {bucket_name} as {s3_object_key}...")
        image_content_type = response.headers.get('Content-Type', 'image/jpeg')
        try:
            s3_client.upload_fileobj(
                io.BytesIO(image_data),
                bucket_name,
                s3_object_key,
                ExtraArgs={'ContentType': image_content_type}
            )
        except ClientError as e:
            logger.error(f"Failed to upload image to S3: {e}")
            continue

        # 4. Update the image URL to CloudFront
        new_img_url = f"https://{cloudfront_domain}/{s3_object_key}"

        # 5. Save to DynamoDB
        item = {
            'artist': artist,
            'title': title,
            'year': year,
            'album': album,
            'image_url': new_img_url
        }
        
        logger.info(f"Saving item to DynamoDB music table: {artist} - {title}")
        try:
            music_table.put_item(Item=item)
        except ClientError as e:
            logger.error(f"Failed to insert item into DynamoDB: {e}")

    logger.info("Data loading completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload dataset to S3 and DynamoDB")
    parser.add_argument("--file", help="Path to the JSON file", default="../2026a2_songs.json")
    parser.add_argument("--bucket", help="S3 Bucket Name (Required)", required=True)
    parser.add_argument("--cloudfront", help="CloudFront domain (e.g. d12345abcdef.cloudfront.net) (Required)", required=True)
    parser.add_argument("--region", help="AWS Region", default="us-east-1")
    
    args = parser.parse_args()
    
    load_data(args.file, args.bucket, args.cloudfront, args.region)
