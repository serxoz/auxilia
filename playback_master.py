import requests as http
from lib.mouse import Mouse
from lib.GPIOInteraction import GPIOInteractor
import os
import time

os.environ['PLAYING'] = 'False'

playing = False
pause_time = 0
paused_at = None
skip = False
# called whenever the physical pause/play button is pressed
def toggle_play_pause():
    global playing
    global paused_at
    global pause_time
    if(m.in_transition):
        return None
    if(playing):
        m.pause()
        playing = False
        paused_at = time.time()
    elif(not playing):
        m.play()
        playing = True
        pause_time += time.time() - paused_at
        print("paused for" + str(time.time() - paused_at))

def skip_song():
    global skip
    skip = True

m = Mouse()
g = GPIOInteractor()
g.set_button_callback(toggle_play_pause)
g.set_button_held_callback(skip_song)
song_url = 'http://127.0.0.1:5000/get_next_song'

def get_next_song():
    try:
        response = http.get(song_url)
    except http.exceptions.ConnectionError:
        print('unable to connect, waiting...')
        time.sleep(10)
        return get_next_song()
    data = response.json()
    while 'error' in data:
        print(data['error'])
        time.sleep(10)
        response = http.get(song_url)
        data = response.json()
    return data


# establish a connection
data = get_next_song()
duration = data['duration'] / 1000.0
start_time = time.time()
m.play_song(data['track_id'])
playing = True
# main loop
while True:
    if time.time() - start_time >= duration + pause_time or skip:
        m.pause()
        data = get_next_song()
        duration = data['duration'] / 1000.0
        m.play_song(data['track_id'])
        start_time = time.time()
        pause_time = 0
        skip = False

