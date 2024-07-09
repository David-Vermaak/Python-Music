from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from mutagen import File
from mutagen.id3 import ID3, APIC
from mutagen.oggvorbis import OggVorbis
from plyer import filechooser
from tempfile import NamedTemporaryFile
import json
import os
import base64


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

        # Create UI elements with icons
        self.title = MDLabel(
            text='Simple Music Player',
            font_style='H5',
            halign='center',
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF")
        )

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
        self.stop_button = MDIconButton(
            icon="stop",
            on_press=self.stop_music,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#FFFFFF"),
            md_bg_color=get_color_from_hex("#0D47A1")
        )

        # Create a scroll view for the song list
        self.scroll_view = ScrollView(size_hint=(1, None), size=(400, 300))
        self.song_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.song_list.bind(minimum_height=self.song_list.setter('height'))
        self.scroll_view.add_widget(self.song_list)

        # Add UI elements to layout
        self.add_widget(self.add_music_button)
        self.add_widget(self.play_pause_button)
        self.add_widget(self.stop_button)
        self.add_widget(self.scroll_view)

        # Populate the song list
        self.update_song_list()

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
            self.update_song_list()

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

    def update_song_list(self):
        self.song_list.clear_widgets()
        for song in self.library.songs:
            item = MDIconButton(
                icon="music-note",
                text=os.path.basename(song),
                theme_text_color="Custom",
                text_color=get_color_from_hex("#FFFFFF"),
                md_bg_color=get_color_from_hex("#1E1E1E"),
                size_hint_y=None,
                height=40
            )
            item.bind(on_press=lambda x, s=song: self.select_song(s))
            self.song_list.add_widget(item)

    def select_song(self, song):
        self.current_song = song
        metadata = self.get_song_metadata(song)
        self.now_playing_title.text = metadata['title']
        self.now_playing_artist.text = metadata['artist']
        self.now_playing_album.text = metadata['album']
        self.stop_music(None)
        self.play_pause_music(None)

    def play_pause_music(self, instance):
        if self.sound and self.sound.state == 'play':
            self.sound.stop()
            self.play_pause_button.icon = "play"
        elif self.current_song:
            if not self.sound:
                self.sound = SoundLoader.load(self.current_song)
            if self.sound:
                self.sound.play()
                self.play_pause_button.icon = "pause"

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