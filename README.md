# Chro1l0-media-player
This is a media player I made, originally designed for playing back music from files.
In its current state, it can only playback music files.
Other features involved are the "audio visualizer" which displays the waveform being played to the speakers, the real time dynamic range compression found in the start_audio_stream_thread function, as well as the ability to download files using pytube. Right clicking on the text input pastes, enter causes it to try to download. Of course, there's also the basics, pause/play, shuffle, and seeking based on the progress bar at the top.

built-in hotkeys and their effects can be found by looking at the on_key_release function in the Main_player file.

You might have issues with the font. I have japanese locale enabled, so you might want to change that to a different system font, but if you ever play a song with unrecognized characters, it'll just turn those characters into boxes (I like japanese text in files so I needed to get a japanese font).
