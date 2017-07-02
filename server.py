from flask import Flask, redirect, request
from flask_socketio import SocketIO, emit
from lib.Queue import Queue
from lib.Song import Song
import requests as http
import json
from base64 import b64encode

app = Flask(__name__)
socketio = SocketIO(app)
queue = Queue()

client_id = 'f3b0c51df1124cc985fd4012b6d55d95'
client_secret = 'e54ca2e0bf394944a1247830443dba3c'

redirect_uri = 'http://127.0.0.1:5000/callback'
#redirect_uri = 'https://example-django-app-dude0faw3.c9users.io/callback'

authorize_uri = 'https://accounts.spotify.com/authorize'
token_uri = 'https://accounts.spotify.com/api/token'

play_uri = 'https://api.spotify.com/v1/me/player/play'
pause_uri = 'https://api.spotify.com/v1/me/player/pause'
track_uri = 'https://api.spotify.com/v1/tracks/'
search_uri = 'https://api.spotify.com/v1/search?type=track&limit=5&q='

access_token = ''
refresh_token = ''

## OAUTH2 

@app.route("/callback")
def callback():
    code = request.args.get('code')
    result = http.post(token_uri, data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    })
    data = result.json()
    print(data)
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    print(access_token)

    return redirect('/static/play.html')
    
@app.route("/authenticate")
def authenticate():
    return redirect(authorize_uri + '?client_id=' + client_id + \
                    '&response_type=code&redirect_uri=' + redirect_uri + '&scope=user-library-read user-modify-playback-state')

## Queue 

@app.route("/add_song")
def add_song():
    track_id = request.args.get('song')
    song_obj = create_song(track_id)
    queue.addSong(song_obj)
    queue_change()
    return 'success'

## Playback Endpoints

@app.route("/resume")
def resume():
    print(get_request(play_uri, call_type='PUT'))
    return 'success'

@app.route("/pause")
def pause():
    print('GOT PAUSE')
    print(get_request(pause_uri, call_type='PUT'))
    return 'success'

## Websocket Events

@socketio.on('client_connected')
def client_connected(data):
    print('a client connected')
    emit('queue_changed', queue.serialize())

@socketio.on('searchbar_changed')
def searchbar_changed(data):
    print('searchbar changing...')
    print('searching for {0}'.format(data))
    response = get_request(search_uri + data.query)
    songs = []
    for track_obj in response.json()['tracks']['items']:
        songs.append(create_song(track_obj))
    emit('suggestions_changed', songs)

def queue_change():
    socketio.emit('queue_changed', queue.serialize())


## Helper Methods

def create_song(track_id):
    min_track_id = track_id[14:]
    response = get_request(track_uri + min_track_id)
    data = response.json()
    track_name = data['name']
    track_artists = ','.join(artist['name'] for artist in data['artists'])
    album_uri = data['album']['images'][0]['url']
    album_name = data['album']['name']
    duration = data['duration_ms']
    return Song(track_name, track_id, track_artists, album_uri, album_name, duration, False)


def get_request(url, call_type='GET', body=None):
    print(url)
    if call_type is 'GET':
        response = http.get(url, headers={'Authorization': 'Bearer ' + access_token})
        if int(response.status_code) >= 400:
            refresh_access_token()
            response = http.get(url, headers={'Authorization': 'Bearer ' + access_token})
    if call_type is 'POST':
        response = http.post(url, data=body, headers={'Authorization': 'Bearer ' + access_token})
        print(response.text)
        if int(response.status_code) >= 400:
            refresh_access_token()
            response = http.post(url, data=body, headers={'Authorization': 'Bearer ' + access_token})
    if call_type is 'PUT':
        response = http.put(url, data=body, headers={'Authorization': 'Bearer ' + access_token})
        print(response.text, response.status_code)
        if int(response.status_code) >= 400:
            refresh_access_token()
            response = http.put(url, data=body, headers={'Authorization': 'Bearer ' + access_token})

    return response


def refresh_access_token():
    body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    string = (client_id + ':' + client_secret).encode('utf-8')
    encoded_string = str(b64encode(string))
    response = http.post(token_uri, data=body, headers={'Authorization': 'Basic ' + encoded_string})
    data = response.json()
    print(data)
    access_token = data['access_token']

## Testing only

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

if __name__ == "__main__":
    socketio.run(app)