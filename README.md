# Chro1l0-media-player
This is a media player I made, originally designed for playing back music from files.
In its current state, it can only playback music files.
Other features involved are the "audio visualizer" which displays the waveform being played to the speakers, the real time dynamic range compression found in the start_audio_stream_thread function, as well as the ability to download files using pytube. Right clicking on the text input pastes, enter causes it to try to download.

built-in hotkeys and their effects can be found by looking at the on_key_release function in the Main_player file.
