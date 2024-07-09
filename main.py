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


class MusicLibrary:
    def __init__(self):
        self.library_file = 'music_library.json'
        self.music_paths = self.load_library()
        self.songs = self.scan_for_songs()

    def load_library(self):
        if os.path.exists(self.library_file):
            with open(self.library_file, 'r') as f:
                return json.load(f)
        return []

    def save_library(self):
        with open(self.library_file, 'w') as f:
            json.dump(self.music_paths, f)

    def add_path(self, path):
        if path not in self.music_paths:
            self.music_paths.append(path)
            self.save_library()
        self.songs = self.scan_for_songs()

    def remove_path(self, path):
        if path in self.music_paths:
            self.music_paths.remove(path)
            self.save_library()
        self.songs = self.scan_for_songs()

    def scan_for_songs(self):
        songs = []
        for path in self.music_paths:
            if os.path.isfile(path):
                songs.append(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.mp3', '.wav', '.ogg')):  # Add more formats if needed
                            songs.append(os.path.join(root, file))
        return songs


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
        self.play_queue.append(song)
        if len(self.play_queue) == 1:
            self.play_song()

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

            if 'APIC:' in audio:
                artwork = audio['APIC:'].data
                with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_file.write(artwork)
                    album_art = temp_file.name
                    print(f"Album art saved to {album_art}")
            else:
                print("No album art available.")
            
            if isinstance(audio, ID3):
                # Handling MP3 files
                title = audio.tags.get('TIT2', title).text[0]
                artist = audio.tags.get('TPE1', artist).text[0]
                album = audio.tags.get('TALB', album).text[0]
                
                # Extract album art
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        artwork = tag.data
                        with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                            temp_file.write(artwork)
                            album_art = temp_file.name
                            print(f"Album art saved to {album_art}")
                        break
            elif isinstance(audio, OggVorbis):
                # Handling OGG files
                title = audio.get('title', [title])[0]
                artist = audio.get('artist', [artist])[0]
                album = audio.get('album', [album])[0]
                
                # OGG files can store album art in a different way
                if 'metadata_block_picture' in audio:
                    artwork_base64 = audio['metadata_block_picture'][0]
                    artwork = base64.b64decode(artwork_base64)
                    with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        temp_file.write(artwork)
                        album_art = temp_file.name
                        print(f"Album art saved to {album_art}")
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'album_art': album_art
            }
        except Exception as e:
            print(f"Error: {e}")
            return {
                'title': os.path.basename(song_path),
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'album_art': None
            }
            
    def add_music(self, instance):
        path = self.select_music_path()
        if path:
            self.library.add_path(path)
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

    def get_song_info(self, song_path):
        try:
            audio = File(song_path)
            
            if audio is None:
                raise ValueError("File could not be opened.")
            
            # Default values
            title = os.path.basename(song_path)
            artist = '-'
            album = '-'
            duration = 0

            if isinstance(audio, MP3):
                # Handling MP3 files
                title = audio.get('title', [title])[0]
                artist = audio.get('artist', [artist])[0]
                album = audio.get('album', [album])[0]
                duration = int(audio.info.length)
            elif isinstance(audio, OggVorbis):
                # Handling OGG files
                title = audio.get('title', [title])[0]
                artist = audio.get('artist', [artist])[0]
                album = audio.get('album', [album])[0]
                duration = int(audio.info.length)
                
            m, s = divmod(duration, 60)
            duration = f'{m:02d}:{s:02d}'

            return {
                'title': title,
                'artist': artist,
                'album': album,
                'duration': duration
            }
        except Exception as e:
            print(f"Error: {e}")
            return {
                'title': os.path.basename(song_path),
                'artist': '-',
                'album': '-',
                'duration': 0
            }
            
    def update_song_table(self):
        self.song_table.clear_widgets()

        # Create headers
        headers = ['Title', 'Artist', 'Album', 'Duration']
        for header in headers:
            self.song_table.add_widget(MDLabel(text=header, halign='center'))

        # Add song info rows
        for song in self.library.songs:
            song_info = self.get_song_info(song)
            title_button = MDFlatButton(text=song_info['title'], size_hint_y=None, height=40)
            title_button.bind(on_press=lambda x, s=song: self.add_to_queue(s))
            self.song_table.add_widget(title_button)

            artist_label = MDLabel(text=song_info['artist'], halign='center')
            self.song_table.add_widget(artist_label)

            album_label = MDLabel(text=song_info['album'], halign='center')
            self.song_table.add_widget(album_label)

            duration_label = MDLabel(text=str(song_info['duration']), halign='center')
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