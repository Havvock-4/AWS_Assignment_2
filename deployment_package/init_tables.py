import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Using us-east-1 as it's typically the default for student labs
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def create_music_table():
    """
    Creates the 'music' table according to the Lossless assignment specification.
    PK: artist
    SK: title
    LSI: ArtistYearIndex (PK: artist, SK: year)
    GSI: AlbumIndex (PK: album, SK: title)
    """
    try:
        table = dynamodb.create_table(
            TableName='music',
            KeySchema=[
                {'AttributeName': 'artist', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'title', 'KeyType': 'RANGE'}   # Sort key
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
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info("Creating 'music' table. Wait until it's ACTIVE...")
        table.wait_until_exists()
        logger.info("Table 'music' is created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info("Table 'music' already exists and is in use.")
        else:
            logger.error(f"Unexpected error: {e}")

def create_login_table():
    """
    Creates the 'login' table for user authentication.
    PK: email
    """
    try:
        table = dynamodb.create_table(
            TableName='login',
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info("Creating 'login' table. Wait until it's ACTIVE...")
        table.wait_until_exists()
        logger.info("Table 'login' is created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info("Table 'login' already exists and is in use.")
        else:
            logger.error(f"Unexpected error: {e}")

def create_user_subscriptions_table():
    """
    Creates the 'user_subscriptions' table to store the songs users have subscribed to.
    PK: email
    SK: song_id (artist_title)
    """
    try:
        table = dynamodb.create_table(
            TableName='user_subscriptions',
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'song_id', 'KeyType': 'RANGE'}   # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'song_id', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info("Creating 'user_subscriptions' table. Wait until it's ACTIVE...")
        table.wait_until_exists()
        logger.info("Table 'user_subscriptions' is created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info("Table 'user_subscriptions' already exists and is in use.")
        else:
            logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    logger.info("Initializing DynamoDB tables...")
    create_music_table()
    create_login_table()
    create_user_subscriptions_table()
    logger.info("Database initialization complete.")
