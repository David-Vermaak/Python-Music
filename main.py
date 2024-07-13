from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from mutagen import File
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from plyer import filechooser
from tempfile import NamedTemporaryFile
import base64
import json
import os
import random
import sqlite3



class MusicLibrary:
    def __init__(self):
        self.db_file = 'music_library.db'
        self.init_db()
        self.songs = self.load_songs()

    def init_db(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_name TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT NOT NULL,
                duration INTEGER NOT NULL,
                album_art_path TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def load_songs(self):
        self.cursor.execute('SELECT * FROM songs')
        rows = self.cursor.fetchall()
        songs = []
        for row in rows:
            duration = row[4]
            m, s = divmod(duration, 60)
            duration = f'{m:02d}:{s:02d}'
            songs.append({
                'id': row[0],
                'song_name': row[1],
                'artist': row[2],
                'album': row[3],
                'duration': duration,
                'album_art_path': row[5]
            })
        return songs


    def save_library(self):
        with open(self.library_file, 'w') as f:
            json.dump(self.music_paths, f)

    def add_path(self, path):
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.ogg')):  # Add more formats if needed
                        song_path = os.path.join(root, file)
                        if not self.song_exists(song_path):
                            metadata = self.get_song_metadata(song_path)
                            self.cursor.execute('''
                                INSERT INTO songs (song_name, artist, album, duration, album_art_path)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (metadata['title'], metadata['artist'], metadata['album'], metadata['duration'], metadata['album_art']))
                            self.conn.commit()
        self.songs = self.load_songs()

    def song_exists(self, song_path):
        self.cursor.execute('SELECT * FROM songs WHERE song_name=?', (os.path.basename(song_path),))
        return self.cursor.fetchone() is not None

    def initial_scan_and_add(self, path):
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.ogg')):  # Add more formats if needed
                        song_path = os.path.join(root, file)
                        if not self.song_exists(song_path):
                            metadata = self.get_song_metadata(song_path)
                            self.cursor.execute('''
                                INSERT INTO songs (song_name, artist, album, duration, album_art_path)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (metadata['title'], metadata['artist'], metadata['album'], metadata['duration'], metadata['album_art']))
                            self.conn.commit()
        elif os.path.isfile(path) and path.endswith(('.mp3', '.wav', '.ogg')):  # Add more formats if needed
            if not self.song_exists(path):
                metadata = self.get_song_metadata(path)
                self.cursor.execute('''
                    INSERT INTO songs (song_name, artist, album, duration, album_art_path)
                    VALUES (?, ?, ?, ?, ?)
                ''', (metadata['title'], metadata['artist'], metadata['album'], metadata['duration'], metadata['album_art']))
                self.conn.commit()
        self.songs = self.load_songs()

    def get_song_metadata(self, song_path):
        try:
            audio = File(song_path)
            
            if audio is None:
                raise ValueError("File could not be opened.")
            
            # Default metadata values
            title = os.path.basename(song_path)
            artist = 'Unknown Artist'
            album = 'Unknown Album'
            album_art = None
            duration = 0

            if 'APIC:' in audio:
                artwork = audio['APIC:'].data
                with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_file.write(artwork)
                    album_art = temp_file.name
                    print(f"Album art saved to {album_art}")
            
            if isinstance(audio, ID3):
                # Handling MP3 files
                title = audio.tags.get('TIT2', title).text[0]
                artist = audio.tags.get('TPE1', artist).text[0]
                album = audio.tags.get('TALB', album).text[0]
                duration = int(audio.info.length)
                m, s = divmod(duration, 60)
                duration = f'{m:02d}:{s:02d}'
                
                # Extract album art
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        artwork = tag.data
                        with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                            temp_file.write(artwork)
                            album_art = temp_file.name
                            print(f"Album art saved to {album_art}")
                        break
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'duration': duration,
                'album_art': album_art
            }
        except Exception as e:
            print(f"Error: {e}")
            return {
                'title': os.path.basename(song_path),
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'duration': 0,
                'album_art': None
            }




class MusicPlayer(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.sound = None
        self.library = MusicLibrary()
        self.current_song = None
        self.paused_position = 0  # Track the position when paused
        self.is_paused = False
        self.shuffle_mode = False
        self.play_queue = []  # Queue to manage song play order

        # Create now playing section
        self.now_playing = MDCard(
            orientation='vertical',
            size_hint=(1, None),
            height="200dp",
            padding="10dp",
            md_bg_color=get_color_from_hex("#1E1E1E")
        )
        
        # Add album art background
        self.album_art = AsyncImage(
            allow_stretch=True,
            keep_ratio=False,
            opacity=0.3
        )
        self.now_playing.add_widget(self.album_art)

        # Create a layout for text information
        self.now_playing_info = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            padding="10dp"
        )
        self.now_playing_title = MDLabel(
            text="Not Playing",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            font_style="H6"
        )
        self.now_playing_artist = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#BBBBBB")
        )
        self.now_playing_album = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#BBBBBB")
        )
        self.now_playing_info.add_widget(self.now_playing_title)
        self.now_playing_info.add_widget(self.now_playing_artist)
        self.now_playing_info.add_widget(self.now_playing_album)

        self.now_playing.add_widget(self.now_playing_info)

        # Add now playing section to the layout
        self.add_widget(self.now_playing)
    

        # Horizontal layout for buttons
        button_layout = BoxLayout(orientation='horizontal')

        # Initialize buttons
        self.add_music_button = MDIconButton(
            icon="plus",
            on_press=self.add_music,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            md_bg_color=get_color_from_hex("#0D47A1")
        )
        self.play_pause_button = MDIconButton(
            icon="play",
            on_press=self.play_pause_music,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            md_bg_color=get_color_from_hex("#0D47A1")
        )
        self.next_button = MDIconButton(
            icon="skip-next",
            on_press=self.next_song,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            md_bg_color=get_color_from_hex("#0D47A1")
        )
        shuffle_button = MDIconButton(
            icon="shuffle-variant",
            on_press=self.shuffle_songs,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            md_bg_color=get_color_from_hex("#0D47A1")
        )

        # Add buttons to horizontal layout
        button_layout.add_widget(self.add_music_button)
        button_layout.add_widget(self.play_pause_button)
        button_layout.add_widget(self.next_button)
        button_layout.add_widget(shuffle_button)

        # Add horizontal button layout to vertical MusicPlayer layout
        self.add_widget(button_layout)

        self.song_table_view = ScrollView(size_hint=(1, 1))
        self.song_table = GridLayout(cols=4, spacing=10, size_hint_y=None)
        self.song_table.bind(minimum_height=self.song_table.setter('height'))
        self.song_table_view.add_widget(self.song_table)

        # Add UI elements to layout
        self.add_widget(self.song_table_view)

        # Populate the song table
        self.update_song_table()

    def add_to_queue(self, song):
        self.play_queue.insert(0, song)

    def play_pause_music(self, instance):

        if self.sound:
            if self.sound.state == 'play':
                self.paused_position = self.sound.get_pos()
                self.sound.stop()
                self.is_paused = True
                self.play_pause_button.icon = "play"
            else:
                if self.is_paused:
                    self.sound.seek(self.paused_position)
                    self.sound.play()
                else:
                    self.play_song()
                self.is_paused = False
                self.play_pause_button.icon = "pause"
        elif self.play_queue:
            self.play_song()
            self.is_paused = False
            self.play_pause_button.icon = "pause"

    def play_song(self):
        if self.play_queue:
            print( "\n\n", self.play_queue, '\n\n')
            self.current_song = self.play_queue.pop(0)
            metadata = self.get_song_metadata(self.current_song)
            self.now_playing_title.text = metadata['title']
            self.now_playing_artist.text = metadata['artist']
            self.now_playing_album.text = metadata['album']

            if self.sound:
                self.sound.stop()
                self.sound.unload()

            self.sound = SoundLoader.load(self.current_song)
            if self.sound:
                self.sound.bind(on_stop=lambda instance: self.play_song())
                if self.is_paused:
                    self.sound.seek(self.paused_position)
                self.sound.play()
                self.play_pause_button.icon = "pause"
                self.is_paused = False 

    def shuffle_songs(self, instance):
        random.shuffle(self.library.songs)
        self.shuffle_mode = True
        self.update_play_queue()

    def update_play_queue(self):
        self.play_queue = list(self.library.songs)  # Reset queue to original or shuffled list
        self.play_song()  # Start playing the first song in the updated queue
            
    def add_music(self, instance):
        path = self.select_music_path()
        if path:
            self.library.initial_scan_and_add(path)
            self.update_song_table()

    def select_music_path(self):
        '''if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE])'''
        
        try:
            path = filechooser.choose_dir() or filechooser.open_file(multiple=True)
            if path:
                return path[0]
            else:
                return None
        except Exception as e:
            print(f"Error selecting path: {e}")
            return None
  
    def update_song_table(self):
        self.song_table.clear_widgets()

        # Create headers
        headers = ['Title', 'Artist', 'Album', 'Duration']
        for header in headers:
            self.song_table.add_widget(MDLabel(text=header, halign='center'))

        # Add song info rows
        for song in self.library.songs:
            self.add_to_queue(song['song_name'])
            title_button = MDFlatButton(text=song['song_name'], size_hint_y=None, height=40)
            title_button.bind(on_press=lambda x, s=song['song_name']: self.add_to_queue(s))
            self.song_table.add_widget(title_button)

            artist_label = MDLabel(text=song['artist'], halign='center')
            self.song_table.add_widget(artist_label)

            album_label = MDLabel(text=song['album'], halign='center')
            self.song_table.add_widget(album_label)

            duration_label = MDLabel(text=song['duration'], halign='center')
            self.song_table.add_widget(duration_label)

    def next_song(self, instance):
        if self.play_queue:
            self.play_song()

    def stop_music(self, instance):
        if self.sound:
            self.sound.stop()
            self.sound.unload()
            self.sound = None
        self.play_pause_button.icon = "play"



class MusicPlayerApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        return MusicPlayer()



if __name__ == '__main__':
    MusicPlayerApp().run()