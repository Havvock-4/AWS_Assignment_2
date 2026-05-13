import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import re
import hashlib



dynamodb = boto3.resource('dynamodb')
music_table = dynamodb.Table('Music')
user_table = dynamodb.Table('Login')
sub_table = dynamodb.Table('User_Subscription')

def valid_email_password(email, password):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    if not re.match(password_regex, password):
        return False

    return True

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def build_cors_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    path = event.get('rawPath', event.get('path', ''))
    method = event.get('requestContext', {}).get('http', {}).get('method', event.get('httpMethod', ''))

    if method == 'OPTIONS':
        return build_cors_response(200, {'message': 'CORS headers set'})

    try:
        if '/api/login' in path and method == 'POST':
            body_str = event.get('body') or '{}'
            body = json.loads(body_str)

            email = body.get('email')
            raw_password = body.get('password', '')
            password = hash_password(raw_password)


            response = user_table.get_item(Key={'email': email})
            

            if 'Item' in response:
                user_data = response['Item']

                if user_data['password'] == password:
                    return build_cors_response(200, {
                        'message': 'Login successful',
                        'user': {
                            'email': email,
                            'name': user_data.get('name')
                        }
                    })

                return build_cors_response(401, {
                    'message': 'Invalid credentials'
                })
            return build_cors_response(404, {'message': 'User not found'})
        
        elif '/api/register' in path and method == 'POST':
            body_str = event.get('body') or '{}'
            body = json.loads(body_str)
            email = body.get('email')
            raw_password = body.get('password', '')
            

            name = body.get('name')

            if(not valid_email_password(email, raw_password)):
                return build_cors_response(400, {'message': 'Invalid email or password format'})

            password = hash_password(raw_password)
            response = user_table.get_item(Key={'email': email})
            if('Item' not in response):
                user_table.put_item(Item={
                    'email': email,
                    'password': password,
                    'name': name
                })
                return build_cors_response(201, {'message': 'User created successfully'})

            else:
                return build_cors_response(409, {'message': 'User already exists'})


        elif '/api/music' in path and method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            title = query_params.get('title', '').strip()
            artist = query_params.get('artist', '').strip()
            album = query_params.get('album', '').strip()
            year = query_params.get('year', '').strip()

            filter_exp = None

            if title: filter_exp = Attr('title').contains(title) if filter_exp is None else filter_exp & Attr('title').contains(title)
            if artist: filter_exp = Attr('artist').contains(artist) if filter_exp is None else filter_exp & Attr('artist').contains(artist)
            if album: filter_exp = Attr('album').contains(album) if filter_exp is None else filter_exp & Attr('album').contains(album)
            if year: filter_exp = Attr('year').eq(year) if filter_exp is None else filter_exp & Attr('year').eq(year)

            response = music_table.scan(FilterExpression=filter_exp) if filter_exp else music_table.scan()
            return build_cors_response(200, {'songs': response['Items']})

        elif '/api/subscriptions' in path and method == 'POST':
            body_str = event.get('body') or '{}'
            body = json.loads(body_str)
            email = body.get('email')
            song_id = body.get('id')

            response = sub_table.get_item(Key = {'email': email})
            subs = response.get('Item', {}).get('subscriptions', [])

            if song_id not in subs:
                subs.append(song_id)

                sub_table.put_item(Item = {'email': email, 'subscriptions': subs})
                return build_cors_response(200, {'message': 'Subscription added successfully'})
            else:
                return build_cors_response(409, {'message': 'Already subscribed'})

        elif '/api/subscriptions' in path and method == 'DELETE':
            body_str = event.get('body') or '{}'
            body = json.loads(body_str)
            # Fallback to query params if body is empty, as some clients don't send bodies with DELETE
            if not body:
                body = event.get('queryStringParameters') or {}
                
            email = body.get('email')
            song_id = body.get('id')

            response = sub_table.get_item(Key = {'email': email})
            subs = response.get('Item', {}).get('subscriptions', [])

            if song_id in subs:
                subs.remove(song_id)
                
                sub_table.put_item(Item = {'email': email, 'subscriptions': subs})
                return build_cors_response(200, {'message': 'Subscription removed successfully'})

            else:
                return build_cors_response(409, {'message': 'Cannot remove subscription as subscription does not exist.'})


        elif '/api/subscriptions' in path and method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            email = query_params.get('email', '')
            if not email:
                return build_cors_response(400, {'message': 'Email is required'})

            response = sub_table.get_item(Key = {'email': email})
            subs = response.get('Item', {}).get('subscriptions', [])

            subscribed_songs = []
            for song_id in subs:
                song_response = music_table.get_item(Key = {'id': song_id})
                if 'Item' in song_response:
                    subscribed_songs.append(song_response['Item'])

            return build_cors_response(200, subscribed_songs)

    except Exception as e:
        print(f"Error: {str(e)}")
        return build_cors_response(500, {'message': 'Internal server error'})

    return build_cors_response(404, {'message': 'Route not found'})


            