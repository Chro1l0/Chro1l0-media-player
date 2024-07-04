import pyaudio
import soundfile as sf
import numpy as np
import threading
import os
import pyloudnorm as pyln
import requests

class AudioPlayer:
    """
    A class for managing audio playback.

    Attributes:
        volume (float): The current volume of the audio playback, between 0 and 1.
        normalization_max (float): The maximum loudness normalization value.
        normalization_min (float): The minimum loudness normalization value.
        normalization_bias (float): The bias for the loudness normalization.
        audio_path (str): The path to the current audio file.
        lock (threading.RLock): A lock for synchronizing access to the audio playback.
        audio_info (sf.Info): Information about the current audio file.
        audio_channels (int): The number of channels in the current audio file.
        audio_frames (int): The number of frames in the current audio file.
        audio_sample_rate (int): The sample rate of the current audio file.
        is_playback_unpaused (threading.Event): An event that is set when the audio playback is unpaused.
        is_stopped (threading.Event): An event that is set when the audio playback is stopped.
        no_audio_loaded (threading.Event): An event that is set when no audio is loaded.
        is_window_focused (threading.Event): An event that is set when the window is focused.
        display_frame_data (np.ndarray): The current display frame data.
        display_skip_rate (int): The rate at which display frames are skipped.
        display_frame_chunk_ratio (int): The ratio of display frames to chunk size.
        current_frame (int): The current frame of the audio playback.
        audio_point_loudness_array (np.ndarray): An array for storing loudness data.
        audio_std_loudness_array (np.ndarray): An array for storing standard deviation loudness data.
    """
    def __init__(self, normalization_max = -3, normalization_min = -20, normalization_bias = 1/8, volume = 1, inital_audio_path = None, display_frame_chunk_ratio = 50, display_skip_rate = 1):
        """
        Initializes an AudioPlayer object.

        Args:
            normalization_max (float): The maximum loudness normalization value. Defaults to -3.
            normalization_min (float): The minimum loudness normalization value. Defaults to -20.
            normalization_bias (float): The bias for the loudness normalization. Defaults to 1/8.
            volume (float): The initial volume of the audio playback. Defaults to 1.
            initial_audio_path (str): The path to the initial audio file. Defaults to None.
            display_frame_chunk_ratio (int): The ratio of display frames to chunk size. Defaults to 50.
            display_skip_rate (int): The rate at which display frames are skipped. Defaults to 1.
        """
        self.volume = volume
        self.normalization_max = normalization_max
        self.normalization_min = normalization_min
        self.normalization_bias = normalization_bias #values closer to 0 = louder overall
        self.audio_path = inital_audio_path
        self.lock = threading.RLock()

        self.audio_info = None
        self.audio_channels = 0
        self.audio_frames = 0
        self.audio_sample_rate = 0

        self.is_playback_unpaused = threading.Event()
        self.is_playback_unpaused.set()
        self.is_stopped = threading.Event()
        self.no_audio_loaded = threading.Event()
        self.no_audio_loaded.set()
        self.is_window_focused = threading.Event()

        self.display_frame_data = None
        if display_skip_rate > 1:
            self.display_skip_rate = display_skip_rate
        else:
            self.display_skip_rate = 1
        self.display_frame_chunk_ratio = display_frame_chunk_ratio
        self.current_frame = 0

        self.audio_point_loudness_array = np.zeros((16))
        self.audio_std_loudness_array = np.zeros((16))#arbitrary number wait, won't this fade in with the way we do things?

    def find_target_loudness(self, audio_data, input_range = 70, target_dynamic_range = 50, loudness_compression_factor = 1, loudness_upper_limit = 10, std__compression_max = 0.975, std_compression_factor = 0.8, expected_std_max = 3.5):
        """
        Calculates the target loudness of the input audio.

        Args:
            audio_data (np.ndarray): The input audio data.
            input_range (float): The input range. Defaults to 70.
            target_dynamic_range (float): The target dynamic range. Defaults to 50.
            loudness_compression_factor (float): The loudness compression factor. Defaults to 1.
            loudness_upper_limit (float): The loudness upper limit. Defaults to 10.
            std_compression_max (float): The maximum standard deviation compression. Defaults to 0.975.
            std_compression_factor (float): The standard deviation compression factor. Defaults to 0.8.
            expected_std_max (float): The expected maximum standard deviation. Defaults to 3.5.

        Returns:
            float: The target loudness.
        """
        loudness_point = max(min(pyln.Meter(self.audio_sample_rate, block_size=len(audio_data)/self.audio_sample_rate).integrated_loudness(audio_data),0),-input_range)
        loudness_point_target_loudness = (((target_dynamic_range-loudness_upper_limit)/target_dynamic_range)
        *target_dynamic_range*((loudness_point+input_range)**(1/loudness_compression_factor))
        *((input_range-1)**((-1)/loudness_compression_factor))-target_dynamic_range)

        audio_std = np.std(np.abs(audio_data))
        # audio_std_target_loudness = (std__compression_max)*(-audio_std**std_compression_factor)*(expected_std_max**(-std_compression_factor))+1
        audio_std_target_loudness = (1-std__compression_max)*(audio_std**std_compression_factor)*expected_std_max**(-std_compression_factor) + std__compression_max
        # audio_std_target_loudness = 1
        target_loudness = min(loudness_point_target_loudness*audio_std_target_loudness,0)
        return target_loudness

#---------------------------- BIG METHOD ----------------------------#

    def start_audio_playback(self, audio_path, chunk_size = 1024):
        """
        Starts the audio playback.

        Args:
            audio_path (str): The path to the audio file.
            chunk_size (int): The chunk size. Defaults to 1024.
        """
        self.is_stopped.set()
        #This wied thing with is_unpaused is to make sure that if we switch while paused it doesn't freeze everything. It'd be stuck waiting forever otherwise
        is_unpaused = self.is_playback_unpaused.is_set()
        self.is_playback_unpaused.set()
        try:
            self.no_audio_loaded.wait()
        finally:
            if not is_unpaused:
                self.is_playback_unpaused.clear()
        if audio_path is not None:
            self.audio_path = audio_path
        #since we only care about the audio_path object attribute, we don't care about the else
        self.no_audio_loaded.clear()
        self.is_stopped.clear()

        def start_audio_stream_thread():
            try:
                p = pyaudio.PyAudio()
                with sf.SoundFile(self.audio_path) as file:
                    audio_info = sf.info(self.audio_path)
                    self.audio_sample_rate = audio_info.samplerate
                    self.audio_frames = audio_info.frames
                    
                    def callback(in_data, frame_count, time_info, status):
                        self.is_playback_unpaused.wait()#what would be nice is a "wait on this or that" thing
                        if self.is_stopped.is_set():
                            return (None, pyaudio.paComplete)
                        
                        with self.lock:
                            file.seek(self.current_frame)
                            self.current_frame += frame_count
                            data = file.read(frames=frame_count, dtype='float32')
                            target_loudness = self.find_target_loudness(data)#I should really look at the entire file at the start. 
                            #I tried avoiding that in case I ever want to load something hours long (hence the stream-y ness of this), but it's really hard getting something good with this
                            data[data == 0] = 1e-12
                            if len(data) == 0:
                                return (None, pyaudio.paComplete)  # Signal end of file

                            if self.is_window_focused.is_set():
                                try:
                                    display_frame_data = file.read(frames=self.display_frame_chunk_ratio*frame_count, dtype='float32')
                                    display_frame_data = display_frame_data[::self.display_skip_rate]
                                    display_frame_data[display_frame_data == 0] = 1e-12
                                    self.display_frame_data = pyln.normalize.peak(display_frame_data,target_loudness)*0.9 + 0.1*display_frame_data
                                except ValueError:
                                    pass
                            normalized_data = pyln.normalize.peak(data, target_loudness)*0.9 + 0.1*data
                            return (normalized_data*self.volume, pyaudio.paContinue)
                    stream = p.open(format=pyaudio.paFloat32,
                                    channels=file.channels,
                                    rate=file.samplerate,
                                    output=True,
                                    frames_per_buffer=chunk_size,  # You can adjust this value
                                    stream_callback=callback)
                    stream.start_stream()
                    while stream.is_active():
                        pass
                    stream.stop_stream()
                    stream.close()
            finally:
                p.terminate()
                self.no_audio_loaded.set()
                with self.lock:
                    self.current_frame = 0
        audio_playing_thread = threading.Thread(target=start_audio_stream_thread, daemon=True)
        audio_playing_thread.start()

    def pause_audio(self):
        """
        Pauses the audio playback.
        """
        if self.audio_frames > 0 and self.is_playback_unpaused is not None:
            self.is_playback_unpaused.clear()

    def unpause_audio(self):
        """
        Unpauses the audio playback.
        """
        if self.audio_frames > 0 and self.is_playback_unpaused is not None:
            self.is_playback_unpaused.set()

    def toggle_pause(self):
        """
        Toggles the pause state of the audio playback.
        """
        if self.is_playback_unpaused.is_set():
            self.pause_audio()
        else:
            self.unpause_audio()

    def seek(self, position, percentage = True):
        """
        Seeks the audio playback to a specific position.

        Args:
            position (float): The position to seek to.
            percentage (bool): Whether the position is a percentage. Defaults to True.
        """
        if self.audio_frames > 0:
            with self.lock:
                if percentage:
                    #given a percentage
                    self.current_frame = int(self.audio_frames*position)
                else:
                    #direct frame
                    self.current_frame = int(position)
    def set_volume(self,target_volume):
        """
        Sets the volume of the audio playback.

        Args:
            target_volume (float): The target volume.
        """
        with self.lock:
            self.volume = min(max(0,target_volume),1)
    def get_display_frames(self):
        """
        Gets the current display frame data.

        Returns:
            np.ndarray: The current display frame data.
        """
        if self.audio_frames > 0:
            with self.lock:
                return self.display_frame_data



#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#

import UI_Widgets
from tkinter import filedialog
import tkinter as tk
class FileManager:
    def __init__(self):
        self.files_to_be_loaded = None

    def open_files(self):
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        root.attributes('-topmost', True)  # Ensure window is on top
        # Open file dialog for selecting multiple files
        file_paths = filedialog.askopenfilenames(title="hjfghjsdgfsdjgssdfsdfssdff (I got mad at this at some point)",filetypes = [('Audio Files', '*.mp3;*.wav;*.ogg;*.flac;*.m4a;*.aac')])
        root.quit()# add something in to make sure you don't stack these on top of eachother, I imagine that'd be annoying and confusing

        files_dict = {}
        for file_path in file_paths:
            files_dict[file_path] = os.path.splitext(os.path.basename(file_path))[0]
        self.files_to_be_loaded = files_dict

    def load_media(self,media_display,default_image, font, extra_images):
        if self.files_to_be_loaded is not None:
            media_display.update_buttons(self.files_to_be_loaded, default_image=default_image, font=font, extra_images=extra_images)
            self.files_to_be_loaded = None



#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#
import subprocess
import pytube
class YoutubeManager:
    '''
    This class is oh so incredibly jank right now
    '''
    def __init__(self, target_mode = "full"):
        self.supported_modes = {"full", "audio", "video"}
        self.mode = "full"
        self.set_mode(target_mode)
        self.temp_file_path = os.path.dirname(__file__) + "\Temp Files"
        self.download_progress = 1
        self.lock = threading.RLock()
    def set_mode(self,target_mode):
        if target_mode in self.supported_modes:
            self.mode = target_mode

    def create_youtube_streams(self,url):
        yt = pytube.YouTube(url)
        audio_stream = None
        video_stream = None
        if self.mode == "full" or self.mode == "audio":
            audio_stream = yt.streams.filter(only_audio=True).first()#black screen
        if self.mode == "full" or self.mode == "video":
            video_stream = yt.streams.filter(adaptive=True).filter(mime_type='video/webm').first()#1080p
        return (yt, audio_stream,video_stream)

    def download_audio_from_url(self, url, download_path = None):
        # callback example: on_progress(stream, chunk, bytes_remaining)
        if download_path is None:
            download_path = os.path.dirname(__file__) + "\Downloads"
        yt, audio_stream, video_stream = self.create_youtube_streams(url)
        output_file_path = None
        file_path = None
        def start_download():
            nonlocal output_file_path
            def progress_callback(stream, chunk, bytes_remaining):
                total_size = stream.filesize
                bytes_downloaded = total_size - bytes_remaining
                percentage_of_completion = bytes_downloaded / total_size
                # print(percentage_of_completion)
                self.download_progress = percentage_of_completion
            yt.register_on_progress_callback(progress_callback)
            #this is unfinished but also don't focus on this it's not that important
            file_path = audio_stream.download(output_path=self.temp_file_path)
            output_file_path =  os.path.join(download_path, os.path.splitext(os.path.basename(file_path))[0] + ".mp3")
            command = [
                'ffmpeg',
                '-i', file_path,
                '-y', #overwrite
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-q:a', '2',  # Quality level (2 is high quality)
                output_file_path
            ]
            with open(os.devnull, 'wb') as devnull:
                subprocess.run(command, stdout=devnull, stderr=devnull)
            for file in os.listdir(self.temp_file_path):
                os.remove(os.path.join(self.temp_file_path, file))
        download_thread = threading.Thread(target=start_download, daemon=True)
        download_thread.start()
    def check_download_progress(self):
        with self.lock:
            return self.download_progress
