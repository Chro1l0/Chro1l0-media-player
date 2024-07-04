import pygame
import pynput
from sys import exit
import threading
import random
import UI_Widgets
import media_handler
import numpy as np
import time
import os
from pygame import freetype
# Initialize Pygame
pygame.init()
resolution = (1920, 1080)
screen = pygame.display.set_mode(resolution)
clock = pygame.time.Clock()
# main_font = pygame.font.Font(None, 24)
main_font = pygame.freetype.SysFont("bizudminchomedium", 24, bold=True)
# main_font = pygame.freetype.SysFont("Meiryo UI", 24, bold=True)
pygame.display.toggle_fullscreen()

exit_flag = False
is_paused = True
is_shuffling = False
click_data = [False,False,False]
was_focused = False

def toggle_pause():
    global audio_player
    global playback_button
    audio_player.toggle_pause()
    if playback_button.display_image == "default":
        playback_button.display_image = "toggle"
    elif playback_button.display_image == "hover":
        playback_button.display_image = "hover toggle"
    elif playback_button.display_image == "toggle":
        playback_button.display_image = "default"
    elif playback_button.display_image == "hover toggle":
        playback_button.display_image = "hover"


# Create a keyboard listener
def CreateListener():
    with pynput.keyboard.Listener(on_press=on_key_release) as listener:
        listener.join()
    return threading.current_thread()
# Define a callback function to handle key events
def on_key_release(key):
    try:
        global audio_player
        global text_input
        if text_input.is_focused:
            text_input.handle_key_press(key)
        else:
            if key.name == "ctrl_r":
                toggle_pause()
            else:
                # IsFocused = pygame.key.get_focused() #All of this was for a previous version. I might re-impliment this however it's unlikely because I'd have to change up how much space the audio visualizer takes too
                # if key.name == "tab" and IsFocused:
                #     global SidebarVisibility
                #     SidebarVisibility = not SidebarVisibility
                if key.name == "space" and is_focused:
                    toggle_pause()
                elif key.name == "esc" and is_focused:
                    global exit_flag 
                    exit_flag = True
                    exit()
    except AttributeError:
        pass

file_manager = media_handler.FileManager()


def pygame_event_handling():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit_flag = True
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                media_display.scroll_position = max(media_display.scroll_position - media_display.scroll_sensitivity, 0)
            elif event.y < 0:
                media_display.scroll_position = min(media_display.scroll_position + media_display.scroll_sensitivity, media_display.get_max_scroll(950))

ui_asset_folder = os.path.dirname(__file__) + r"\UI Assets"
NecessaryImages = {
    "Play": ui_asset_folder+r"\Play Button (Dark).png",
    "Play Hover": ui_asset_folder+r"\Play Button (Dark Hovered).png",
    "Pause": ui_asset_folder+r"\Pause Button (Dark).png",
    "Pause Hover": ui_asset_folder+r"\Pause Button (Dark Hovered).png",
    "Shuffle": ui_asset_folder+r"\Shuffle (Smooth).png",
    "Shuffle Highlight": ui_asset_folder+r"\Shuffle Highlighted (Smooth).png",
    "Top Bar": ui_asset_folder+r"\Top Bar (Dark).png",
    "Sidebar": ui_asset_folder+r"\Sidebar Default.png",
    "Load": ui_asset_folder+r"\Load.png",
    "Label": ui_asset_folder+r"\Label (476x50).png",
    "Label Hover": ui_asset_folder+r"\Label (Highlighted).png",
    "Label Select": ui_asset_folder+r"\Label (Selected).png",
    "Volume": ui_asset_folder+r"\Volume.png",
    "Volume Holder": ui_asset_folder+r"\Volume Holder.png",
    "Text Input": ui_asset_folder+r"\Text Input.png",
}

#Now loading stuff
loaded_images = {}
for label,path in NecessaryImages.items():
    loaded_images[label] = pygame.image.load(path)

#widget initialization
playback_button = UI_Widgets.Button(loaded_images["Play"], extra_images={"toggle":loaded_images["Pause"],"hover":loaded_images["Play Hover"],"hover toggle":loaded_images["Pause Hover"]})
playback_button.position = (1920/2,130) - playback_button.image_info["default"][1]/2


shuffler_button = UI_Widgets.Button(loaded_images["Shuffle"],extra_images={"toggle":loaded_images["Shuffle Highlight"]})
shuffler_button.position = (1920-128,65) - shuffler_button.image_info["default"][1]/2

text_input = UI_Widgets.TextInput(loaded_images["Text Input"],main_font,position=((1100),40), text_color=(0,255,255))
download_progress_bar = UI_Widgets.ProgressBar(3,635,position=((1100),40+50+2))



def toggle_shuffle():
    global is_shuffling
    is_shuffling = not is_shuffling
shuffler_button.on_toggle_call = lambda: toggle_shuffle()
shuffler_button.on_untoggle_call = lambda:toggle_shuffle()

load_file_button = UI_Widgets.Button(loaded_images["Load"], is_toggle_button=False)
load_file_button.position = (128,65) - load_file_button.image_info["default"][1]/2

def start_load_file_dialog():
    def thread_function():
        file_manager.open_files()
    thread = threading.Thread(target=thread_function, daemon = True)
    thread.start()

load_file_button.on_toggle_call = start_load_file_dialog

media_display = UI_Widgets.ButtonList(position=(0,128), scroll_sensitivity=75)

media_progress_bar = UI_Widgets.ProgressBar(5, 1920, hover_thickness=10)
volume_bar = UI_Widgets.ProgressBar(4,100,position=((1920/2)-50,50), drag_tolerance=13, vert_drag_tolerance=3)
volume_bar.progress = 1

top_bar_image = UI_Widgets.WidgetImage(image=loaded_images["Top Bar"])
sidebar_image = UI_Widgets.WidgetImage(image=loaded_images["Sidebar"], position=(0,129))
volume_container = UI_Widgets.WidgetImage(loaded_images["Volume Holder"],position=(895,47))
volume_icon = UI_Widgets.WidgetImage(loaded_images["Volume"],position=(860,19))



KeyListenerThread = threading.Thread(target=CreateListener, daemon=True)
KeyListenerThread.start()

audio_player = media_handler.AudioPlayer(display_frame_chunk_ratio=20, display_skip_rate=4)

audio_visualizer = UI_Widgets.AudioVisualizer(audio_player, 1440, 950, pygame.Vector2(480,130))

yt_manager = media_handler.YoutubeManager(target_mode="audio")

def url_enter(url,yt_manager):
    yt_manager.download_audio_from_url(url)
media_display.on_button_toggle = lambda path: audio_player.start_audio_playback(path,chunk_size=2048)
text_input.on_enter = lambda text_input_object: url_enter(text_input_object.text, yt_manager)
media_progress_bar.on_progress_click = lambda progress: (audio_player.seek(progress))

playback_button.on_toggle_call = lambda: audio_player.pause_audio()
playback_button.on_untoggle_call = lambda: audio_player.unpause_audio()

focused_button = None


ui_layer_01 = [sidebar_image, audio_visualizer]
ui_layer_1 = [media_display]
ui_layer_2 = [top_bar_image,volume_container, volume_icon]
ui_layer_3 = [playback_button,shuffler_button,load_file_button,media_progress_bar,volume_bar,text_input, download_progress_bar]#last things to be rendered (on top)

node_tree = UI_Widgets.Node([ui_layer_01,ui_layer_1,ui_layer_2,ui_layer_3])

while True:
    screen.fill((0,0,0))
    pygame_event_handling()
    is_focused = pygame.key.get_focused()
    if is_focused and not was_focused:
        audio_player.is_window_focused.set()
    elif was_focused and not is_focused:
        audio_player.is_window_focused.clear()
    if exit_flag:
        pygame.quit()
        exit()
        break
    #mouse handling
    mouse_position = pygame.mouse.get_pos()
    new_click_data = pygame.mouse.get_pressed()
    click_comparer = [new != old and new for new, old in zip(new_click_data, click_data)]# if they aren't the same and the new thing is pressed, return true
    mouse_state_changed = any(click_comparer)
    if new_click_data != click_data and new_click_data[0]:#this evaluates to true when you click on this with LMB
        text_input.is_focused = False
    audio_visualizer.update_audio_display_data(audio_player.get_display_frames(), mode="channels")

    node_tree.handle_mouse(mouse_position,new_click_data,click_data)
    file_manager.load_media(media_display,loaded_images["Label"],font=main_font,extra_images={"hover":loaded_images["Label Hover"],"toggle":loaded_images["Label Select"]})
    if audio_player.audio_frames > 0:
        media_progress_bar.progress = audio_player.current_frame/audio_player.audio_frames
    if audio_player.no_audio_loaded.is_set() and audio_player.audio_frames > 0:
        #if we didn't just load the thing and nothing's playing, do this
        if is_shuffling:
            media_display.random_toggle()
        else:
            media_display.sequential_toggle()

    download_progress_bar.progress = yt_manager.check_download_progress()
    audio_player.set_volume(volume_bar.progress)
    click_data = new_click_data
    mouseover_not_found = True
    #end of mouse handling
    if is_focused:
        node_tree.render(screen)
        pygame.display.update()

    clock.tick(30)
    was_focused = is_focused

    