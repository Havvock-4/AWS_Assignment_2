import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app)

# Initialize Boto3 DynamoDB resource
# Note: we use us-east-1 as default for the lab, but production could pull from env vars.
REGION = os.environ.get('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# Tables
login_table = dynamodb.Table('login')
music_table = dynamodb.Table('music')
subscriptions_table = dynamodb.Table('user_subscriptions')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password') # In a real app, hash this!
    username = data.get('username')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        # Use ConditionExpression attribute_not_exists to ensure email is unique
        # This guarantees Lossless write without a race condition
        login_table.put_item(
            Item={
                'email': email,
                'password': password,
                'username': username
            },
            ConditionExpression='attribute_not_exists(email)'
        )
        return jsonify({"message": "User registered successfully."}), 201
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({"error": "User with this email already exists."}), 409
        else:
            return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        response = login_table.get_item(Key={'email': email})
        user = response.get('Item')

        if not user or user.get('password') != password:
            return jsonify({"error": "Invalid email or password."}), 401

        # We return the user info (excluding password in a real app)
        return jsonify({
            "message": "Login successful.", 
            "user": {"email": user['email'], "username": user.get('username')}
        }), 200
    except ClientError as e:
         return jsonify({"error": str(e)}), 500

@app.route('/api/query', methods=['GET'])
def query_music():
    artist = request.args.get('artist')
    year = request.args.get('year')
    title = request.args.get('title')
    album = request.args.get('album')

    try:
        # 1. Title Query (requires Artist for Partition Key)
        if artist and title:
            # We can uniquely identify the song using the base table
            response = music_table.get_item(Key={'artist': artist, 'title': title})
            item = response.get('Item')
            return jsonify([item] if item else []), 200

        # 2. Artist + Year -> Query LSI
        elif artist and year:
            response = music_table.query(
                IndexName='ArtistYearIndex',
                KeyConditionExpression=Key('artist').eq(artist) & Key('year').eq(year)
            )
            return jsonify(response.get('Items', [])), 200

        # 3. Only Artist -> Query base table using Partition Key
        elif artist:
            # If we also have 'album' as an extra filter, we use FilterExpression
            filter_exp = None
            if album:
                filter_exp = Attr('album').eq(album)
            
            if filter_exp:
                response = music_table.query(
                    KeyConditionExpression=Key('artist').eq(artist),
                    FilterExpression=filter_exp
                )
            else:
                response = music_table.query(
                    KeyConditionExpression=Key('artist').eq(artist)
                )
            return jsonify(response.get('Items', [])), 200
        
        # 4. Only Album -> Query GSI
        elif album:
            # We query the AlbumIndex GSI. Since GSI doesn't require the main PK
            response = music_table.query(
                IndexName='AlbumIndex',
                KeyConditionExpression=Key('album').eq(album)
            )
            return jsonify(response.get('Items', [])), 200
        
        else:
             return jsonify({"error": "Please provide either 'artist', 'album', or 'artist'+'year'."}), 400

    except ClientError as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "User email is required"}), 400

    try:
        # Retrieve all subscriptions for the user
        response = subscriptions_table.query(
            KeyConditionExpression=Key('email').eq(email)
        )
        subscriptions = response.get('Items', [])
        
        # We need to fetch the actual song details from the music table
        # song_id is formatted as artist::title to make it easy to separate
        subscribed_songs = []
        for sub in subscriptions:
            song_id = sub['song_id']
            if '::' in song_id:
                artist, title = song_id.split('::', 1)
                music_response = music_table.get_item(Key={'artist': artist, 'title': title})
                if 'Item' in music_response:
                    subscribed_songs.append(music_response['Item'])

        return jsonify(subscribed_songs), 200
    except ClientError as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    email = data.get('email')
    artist = data.get('artist')
    title = data.get('title')

    if not email or not artist or not title:
        return jsonify({"error": "Email, artist, and title are required"}), 400

    song_id = f"{artist}::{title}"
    try:
        subscriptions_table.put_item(
            Item={
                'email': email,
                'song_id': song_id,
                'artist': artist,
                'title': title
            }
        )
        return jsonify({"message": "Subscribed successfully"}), 201
    except ClientError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    data = request.json
    email = data.get('email')
    artist = data.get('artist')
    title = data.get('title')

    if not email or not artist or not title:
        return jsonify({"error": "Email, artist, and title are required"}), 400

    song_id = f"{artist}::{title}"
    try:
        subscriptions_table.delete_item(
            Key={
                'email': email,
                'song_id': song_id
            }
        )
        return jsonify({"message": "Unsubscribed successfully"}), 200
    except ClientError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run natively for local testing, typically port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
