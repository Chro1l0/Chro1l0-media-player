import pygame
import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Union, Callable
import pynput
import pyperclip as clipboard


class Button:
    """
    A simple button object that displays a default image when drawn unless another image index is given.
    The reason that is_mouseover doesn't auto render with the hover image or default when false is because that is not always desireable, and can be done simply with:

    if Btn.is_mouseover(mouse_position):
        Btn.render(screen,image_type = "hover")
    else:
        Btn.render(screen)
    """
    def __init__(self, default_image: pygame.Surface, extra_images: Optional[Dict[str, pygame.Surface]] = None, position: pygame.Vector2 = pygame.Vector2(), is_toggle_button:bool = True) -> None:
        """
        Initializes a Button object.

        Args:
            default_image (pygame.Surface): The default image for the button.
            extra_images (Dict[str, pygame.Surface], optional): A dictionary of extra images for the button. Defaults to None.
            position (pygame.Vector2, optional): The position of the button. Defaults to pygame.Vector2().

        Raises:
            ValueError: If extra_images is not a dictionary.
            ValueError: If the values of extra_images are not of type pygame.Surface.
        """
        if extra_images and not isinstance(extra_images, dict):
            raise ValueError("extra_images must be a dictionary")
        if extra_images and not all(isinstance(image, pygame.Surface) for image in extra_images.values()):
            raise ValueError("All values in extra_images must be of type pygame.Surface")

        self.image_info = {"default": [default_image, pygame.Vector2(default_image.get_width(), default_image.get_height())]}

        if extra_images is not None:
            for key, image in extra_images.items():
                self.image_info[key] = [image, pygame.Vector2(image.get_width(), image.get_height())]

        self.position: pygame.Vector2 = position
        self.display_image = "default"
        self.is_toggle = is_toggle_button
        self.on_toggle_call = None
        self.on_untoggle_call = None
    
    def render(self, screen: pygame.Surface, bounding_area: Optional[pygame.Rect] = None, position: Optional[Union[pygame.Vector2, tuple]] = None, offset: Optional[Union[pygame.Vector2, tuple]] = (0,0)) -> None:
        """
        Blits the button's current image (as specified by display_image) at the button's position.

        If a new position is given, then the button moves to that position and stays there.
        bounding_area defines the area that checks if the button should be rendered.
        "bounding_area" is defined by a pygame Rect object, and defaults to the screen dimensions if None.

        Args:
            screen (pygame.Surface): The screen where the button should be rendered.
            bounding_area (pygame.Rect, optional): The area where the button should be rendered. Defaults to None.
            position (pygame.Vector2, optional): The new position of the button. Defaults to None.

        Raises:
            KeyError: If Button.display_image and default_dict are not int the image_info dictionary.
        """
        if position is not None and not isinstance(position,(pygame.Vector2,tuple)):
            raise TypeError(f"Expected a pygame.Vector2 or a tuple of ints for postion, but got a {type(position)}")
        elif isinstance(position, tuple) and len(position) != 2:
            raise ValueError(f"position must contain exactly two values, not {len(position)}")
        if position is not None:
            self.position = position
        if bounding_area is not None and not isinstance(bounding_area,pygame.Rect):
            raise TypeError(f"Expected a pygame.Rect for bounding_area, but got {type(bounding_area)}")
        if bounding_area is None:
            bounding_area = pygame.rect.Rect(0, 0, screen.get_width(), screen.get_height())
        if not self.is_in_area(bounding_area,offset=offset):
            return

        try:
            screen.blit(self.image_info[self.display_image][0], self.position + offset)
        except KeyError:
            # If the self.display_image is not found in the dictionary, try to blit the default image
            try:
                if self.display_image == "hover toggle":
                    try:
                        screen.blit(self.image_info["toggle"][0], self.position + offset)
                        return
                    except:
                        pass
                    #on fail and on "no, this isn't hover toggle" should make this next part happen
                screen.blit(self.image_info["default"][0], self.position + offset)
            except KeyError:
                # If the default image is also not found, raise an error
                raise KeyError(f"Button.display_image '{self.display_image}' and the default image are both missing in image_info dictionary")

    def is_mouseover(self, mouse_position: pygame.Vector2, mouseover_image_key: str = "default") -> bool:
        """
        Checks if the mouse is over the button's image (as specified by mouseover_image_key), taking into account opacity.

        Args:
            mouse_position (pygame.Vector2): The position of the mouse.
            mouseover_image_key (str, optional): The key of the image to check. Defaults to "default".

        Returns:
            bool: True if the mouse is over the image, False otherwise.

        Raises:
            KeyError: if mouseover_image_key is not found in the image_info dictionary
        """
        ALPHA_THRESHOLD = 125
        try:
            relative_position = pygame.Vector2(mouse_position) - self.position
            mouseover_image = self.image_info[mouseover_image_key.lower()][0]
            if mouseover_image.get_rect().collidepoint(relative_position):
                color = mouseover_image.get_at((int(relative_position.x),int(relative_position.y)))
                if color.a > ALPHA_THRESHOLD:
                    return True
        except KeyError:
            # Handle the case where the mouseover_image_key is not found
            print(f"Image key '{mouseover_image_key}' not found.")
        return False
    
    def is_in_area(self, bounding_area: pygame.Rect, image_type: str = "default",  offset:pygame.Vector2=pygame.Vector2()) -> bool:
        """
        Check if the image is in the given area.

        Args:
            bounding_area (pygame.Rect): The area to check.
            image_type (str, optional): The type of the image. Defaults to "default".

        Returns:
            bool: True if the image is in the area, False otherwise.

        Raises:
            ValueError: If the given image type is not in the self.image_info dictionary.
            TypeError: If the bounding_area is not a pygame.Rect.
        """
        if not isinstance(bounding_area, pygame.Rect):
            raise TypeError(f"Expected a pygame.Rect, but got {type(bounding_area)}")
        if image_type not in self.image_info:
            raise ValueError(f"Unknown image type: {image_type}")
        # Move the image rectangle to the position and get its rectangle
        image_rect = self.image_info[image_type][0].get_rect().move(self.position+offset)
        # Check if the image rectangle collides with the bounding area
        return bounding_area.colliderect(image_rect)
    
    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        if self.is_mouseover(mouse_position):
            if self.display_image == "toggle" or self.display_image == "hover toggle":
                self.display_image = "hover toggle"
            else:
                self.display_image = "hover"
            if new_pressed_button_state != held_button_state and new_pressed_button_state[0]:#this evaluates to true when you click on this with LMB
                if self.is_toggle:
                    #should be pressed on. If it's toggle, then we toggle it, otherwise we don't
                    if self.display_image == "hover toggle":
                        self.display_image = "hover"
                        if self.on_untoggle_call:
                            self.on_untoggle_call()
                    else:
                        self.display_image = "hover toggle"
                        if self.on_toggle_call:
                            self.on_toggle_call()
                else:
                    self.on_toggle_call()
        elif self.display_image == "hover":
            #reset, because if it was hover and we aren't on it anymore it shouldn't be hover
            self.display_image = "default"
        elif self.display_image == "hover toggle":
            self.display_image = "toggle"



#---------------------------- CHILD OBJECT ----------------------------#

class TextButton(Button):
    """
    A button that displays text. images are backgrounds, which should be close to a long rectangle to make sure it fills the shape correctly, the text will be centered within the bounds of the drawn image.
    The default color of the text is (0, 229, 179) because I like that color
    """
    def __init__(self,default_image, font:pygame.font.Font, text_color = (0, 229, 179), display_text = "Default Text", text_padding = 20, extra_images=None, position = pygame.Vector2()):
        super().__init__(default_image, extra_images=extra_images, position = position)
        self.font = font
        self.text_color = text_color
        self.display_text = display_text
        self.text_padding = text_padding
    
    def render(self, screen: pygame.Surface, bounding_area: Optional[pygame.Rect] = None, position: Optional[Union[pygame.Vector2, tuple]] = None, offset: Optional[Union[pygame.Vector2, tuple]] = (0,0)) -> None:
        """
        Blits the button's background image (as specified by display_image) at the button's position, and then renders the text on top of it.

        If a new position is given, then the button moves to that position and stays there.
        Bounding_area defines the area that checks if the button should be rendered.
        "Bounding_area" is defined by a pygame Rect object, and defaults to the screen dimensions if None.
        It then renders the text in the center of the image, scaled to fit in the bounds of the rectangle-like image.

        Args:
            screen (pygame.Surface): The screen where the button should be rendered.
            bounding_area (pygame.Rect, optional): The area where the button should be rendered. Defaults to None.
            display_image (str, optional): The type of image to be rendered. Defaults to "default".
            position (pygame.Vector2, optional): The new position of the button. Defaults to None.

        Raises:
            ValueError: If display_image is not a string, or if display_image does not exist in the image_info dictionary.
            KeyError: If display_image and default_dict are not int the image_info dictionary.
        """
        if position is not None and not isinstance(position,(pygame.Vector2,tuple)):
            raise TypeError(f"Expected a pygame.Vector2 or a tuple of ints for postion, but got a {type(position)}")
        elif isinstance(position, tuple) and len(position) != 2:
            raise ValueError(f"position must contain exactly two values, not {len(position)}")
        if position is not None:
            self.position = position
        if bounding_area is not None and not isinstance(bounding_area,pygame.Rect):
            raise TypeError(f"Expected a pygame.Rect for bounding_area, but got {type(bounding_area)}")
        if bounding_area is None:
            bounding_area = pygame.rect.Rect(0, 0, screen.get_width(), screen.get_height())
        if not self.is_in_area(bounding_area,offset=offset):
            return
        try:
            display_image = self.image_info[self.display_image]
        except KeyError:
            try:
                display_image = self.image_info["default"]
            except KeyError:
                raise KeyError(f"Button.display_image '{display_image}' and the default image are both missing in image_info dictionary")
        
        text_surface, rect = self.font.render(str(self.display_text),self.text_color)
        rendered_text = text_surface.convert_alpha()
        available_width = display_image[1][0] - self.text_padding
        
        text_offset = pygame.Vector2()

        if rendered_text.get_width() > available_width:
            # If the text is wider than the available width, scale it down
            rendered_text = pygame.transform.scale(rendered_text, (available_width, rendered_text.get_height()))
            text_offset += pygame.Vector2(self.text_padding/2,0)
        
        width_difference = available_width - rendered_text.get_width()
        height_difference = display_image[1][1] - rendered_text.get_height()
        text_offset += pygame.Vector2(width_difference, height_difference) / 2  # Maximum width will be text_padding/2

        screen.blit(display_image[0], self.position + offset)
        screen.blit(rendered_text, self.position + text_offset + offset)


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#


class ButtonList:
    def __init__(self, position: Optional[Union[pygame.Vector2, tuple]] = None, scroll_sensitivity: Optional[float] = 1) -> None:
        """
        This is intended to take a list of TextButtons (defined elsewhere), and display them on a pygame screen. 
        I plan to have support for different shaped displays, but for now it should be a vertical thing that I can scroll though by changing the scroll_position variable.
        Has optional perameters in case you want to give the Text button aditional images for when it's hovered or toggled (the string entry must exist in the buttons too)

        Args:
            button_dict (Optional[Dict[str, TextButton]], optional): A dictionary of TextButton objects. Defaults to None.
            position (Optional[Union[pygame.Vector2, tuple]], optional): The position of the ButtonList. Defaults to None.
            scroll_sensitivity (Optional[float], optional): The sensitivity of scrolling. Defaults to 1.

        Raises:
            ValueError: If button_dict is not a dictionary or None.
            ValueError: If position is not a pygame.Vector2, tuple or None.
            ValueError: If scroll_sensitivity is not a number.
        """
        if position is not None and not isinstance(position, (pygame.Vector2, tuple)):
            raise ValueError("position must be a pygame.Vector2, tuple or None.")
        self.position = pygame.Vector2(0, 0)
        if position is not None:
            self.position = pygame.Vector2(position)

        self.button_dict = {}
        self.sorted_keys = []
        self.toggled_buttons = set()
        self.is_exclusive = True

        if not isinstance(scroll_sensitivity, (int, float)):
            raise ValueError("scroll_sensitivity must be a number.")
        self.scroll_position = 0
        self.scroll_sensitivity = scroll_sensitivity #This is used to say how much a scroll up/down should affect this. Technically, isn't required because you can just do it externally, but it's nice to have here
        self.on_button_toggle = None
        self.on_button_untoggle = None
    
    def render(self, screen: pygame.Surface, bounding_area: Optional[pygame.Rect] = None, position: Optional[Union[pygame.Vector2, tuple]] = None) -> None:
        """
        Renders all the buttons in a vertical list.

        Args:
            screen (pygame.Surface): The screen where the buttons should be rendered.
            bounding_area (Optional[pygame.Rect], optional): The area where the buttons should be rendered. Defaults to None.
            position (Optional[Union[pygame.Vector2, tuple]], optional): The position of the ButtonList. Defaults to None.

        Returns:
            None: None
        """
        if bounding_area is None:
            bounding_area = pygame.rect.Rect(0, 0, screen.get_width(), screen.get_height())
        
        for key in self.sorted_keys:
            button = self.button_dict[key]
            button.render(screen, bounding_area=bounding_area, offset=self.position-pygame.Vector2(0,self.scroll_position))
    
    def update_buttons(self, button_dict: Dict[str, str], default_image, font: pygame.font.Font, text_color=(0, 229, 179), text_padding=20, extra_images: Optional[Dict[str, pygame.Surface]]=None) -> None:
        """
        Updates the buttons in the ButtonList.

        Args:
            button_dict (Dict[str, str]): A dictionary of display text values.
            default_image: The default image for the buttons.
            font (pygame.font.Font): The font for the button text.
            text_color (Tuple[int, int, int], optional): The color of the button text. Defaults to (0, 229, 179).
            text_padding (int, optional): The padding for the button text. Defaults to 20.
            extra_images (Optional[Dict[str, pygame.Surface]], optional): A dictionary of extra images for the buttons. Defaults to None.

        Raises:
            ValueError: If a value in the dictionary is not a string.
        """
        try:
            for organizer, display_text in button_dict.items():
                if not isinstance(display_text, str):
                    raise ValueError(f"Value for key '{organizer}' is not a string.")
                self.button_dict[organizer] = TextButton(default_image, font, text_color, display_text, text_padding, extra_images)
            self.sorted_keys = sorted(self.button_dict.keys())
            self.calculate_button_positions()
        except ValueError as e:
            print(f"Error: {e}")
    
    def calculate_button_positions(self) -> None:
        """
        Calculate the positions of the buttons based on their order in the dictionary.

        Returns:
            None: None
        """
        button_height = 0
        for key in self.sorted_keys:
            button = self.button_dict[key]
            button.position = pygame.Vector2(0,button_height)
            button_height += button.image_info["default"][1][1]#height can change depending on displayed image
    
    def get_max_scroll(self, bounding_height) -> int:
        """
        Calculates the maximum scroll amount based on the total height of all buttons and the height of the bounding area.

        Args:
            bounding_height (int): The height of the bounding area.

        Returns:
            int: The maximum scroll amount.
        """
        button_height = 0
        for button in self.button_dict.values():
            button_height += button.image_info[button.display_image][1][1]  # height can change depending on displayed image
        return max(0, button_height - bounding_height)
    
    def handle_exclusive_toggle_mouse(self, mouse_position, click_state, mouse_button):
        relative_mouse_position = mouse_position-self.position
        is_in_bounds = True
        if relative_mouse_position[1] < 0:
            is_in_bounds = False
        relative_mouse_position += pygame.Vector2(0,self.scroll_position)
        buttons_to_remove = []
        for organizer, button in self.button_dict.items():
            if button.is_mouseover(relative_mouse_position) and is_in_bounds:
                if click_state and mouse_button == 1:  # Left mouse button
                    if button.display_image == "hover":
                        button.display_image = "toggle"
                        self.toggled_buttons.add(button)
                        if self.on_button_toggle:
                            self.on_button_toggle(organizer)
                    elif button.display_image == "toggle":
                        button.display_image = "hover"
                        self.toggled_buttons.remove(button)
                        if self.on_button_untoggle:
                            self.on_button_untoggle(organizer)
                    for b in self.toggled_buttons:
                        if b != button:
                            b.display_image = "default"
                elif click_state and mouse_button == 3:  # Right mouse button
                    buttons_to_remove.append(organizer)
                else:
                    if button.display_image != "toggle":
                        button.display_image = "hover"
            else:
                if button.display_image != "toggle":
                    button.display_image = "default"
        for organizer in buttons_to_remove:
            del self.button_dict[organizer]
        self.sorted_keys = sorted(self.button_dict.keys())
        self.calculate_button_positions()
    
    def handle_multi_toggle_mouse(self,mouse_position,click_state):
        """
        NOT YET IMPLIMENTED, also not important yet
        """
        pass
    
    def random_toggle(self):
        # Get a list of all buttons
        buttons = list(self.button_dict.values())
        
        # Filter out buttons that are already toggled
        untoggled_buttons = [button for button in buttons if button.display_image != "toggle"]
        
        # If there are untoggled buttons, select one at random and toggle it
        if untoggled_buttons:
            random_button = random.choice(untoggled_buttons)
            random_button.display_image = "toggle"
            self.toggled_buttons.add(random_button)
            if self.on_button_toggle:
                for organizer, button in self.button_dict.items():
                    if button == random_button:
                        self.on_button_toggle(organizer)
                        break
                
            # Set all other buttons back to default
            for button in buttons:
                if button != random_button:
                    button.display_image = "default"
                    for organizer, b in self.button_dict.items():
                        if b == button:
                            if self.on_button_untoggle:
                                self.on_button_untoggle(organizer)
                    
    def sequential_toggle(self):
        # Get a list of all buttons in sorted order
        sorted_buttons = [(self.button_dict[key], key) for key in self.sorted_keys]
        
        # Find the currently toggled button
        toggled_button = next(((button, organizer) for button, organizer in sorted_buttons if button.display_image == "toggle"), None)
        
        # If there is a toggled button, toggle the next one
        if toggled_button:
            index = sorted_buttons.index(toggled_button)
            next_index = (index + 1) % len(sorted_buttons)
            next_button, next_organizer = sorted_buttons[next_index]
            toggled_button[0].display_image = "default"
            if self.on_button_untoggle:
                self.on_button_untoggle(toggled_button[1])
            next_button.display_image = "toggle"
            self.toggled_buttons.clear()
            self.toggled_buttons.add(next_button)
            if self.on_button_toggle:
                self.on_button_toggle(next_organizer)
        else:
            # If there is no toggled button, toggle the first one
            first_button, first_organizer = sorted_buttons[0]
            first_button.display_image = "toggle"
            self.toggled_buttons.add(first_button)
            if self.on_button_toggle:
                self.on_button_toggle(first_organizer)
        
    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        click_state = new_pressed_button_state != held_button_state and any(new_pressed_button_state)
        mouse_button = None
        for i, state in enumerate(new_pressed_button_state):
            if state and not held_button_state[i]:
                mouse_button = i + 1
                break
        if self.is_exclusive:
            self.handle_exclusive_toggle_mouse(mouse_position, click_state, mouse_button)
        else:
            #This will break right now, unless I got lazy and just never removed this
            self.handle_multi_toggle_mouse(mouse_position,click_state)


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#


class ProgressBar:
    """
    A progress bar widget.

    Attributes:
    - thickness (int): The thickness of the progress bar.
    - length (int): The length of the progress bar.
    - hover_thickness (int): The thickness of the progress bar when hovered.
    - position (pygame.Vector2 or tuple): The position of the progress bar.
    - drag_tolerance (int): The tolerance for mouse dragging.
    - on_progress_click (Callable[[float], None]): A callback function to be called when the progress bar is clicked.
    """

    def __init__(self, thickness: int, length: int, hover_thickness: Optional[int] = None, position: Union[pygame.Vector2, tuple] = pygame.Vector2(), drag_tolerance: int = 5, vert_drag_tolerance=0) -> None:
        """
        Initializes a new progress bar.

        Args:
        - thickness (int): The thickness of the progress bar.
        - length (int): The length of the progress bar.
        - hover_thickness (int, optional): The thickness of the progress bar when hovered. Defaults to None.
        - position (pygame.Vector2 or tuple, optional): The position of the progress bar. Defaults to pygame.Vector2().
        - drag_tolerance (int, optional): The tolerance for mouse dragging (horizontal). Defaults to 5.
        - vert_drag_tolerance (int, optional): The tolerance for mouse dragging (vertical). Defaults to 0.
        """
        self.thickness = thickness
        self.hover_thickness = thickness
        if hover_thickness is not None:
            self.hover_thickness = hover_thickness
        self.length = length
        self.position = position
        self._progress = 0
        self.is_hovered = False
        self.drag_tolerance = drag_tolerance
        self.vert_drag_tolerance = vert_drag_tolerance
        self.on_progress_click: Callable[[float], None] = None

    def render(self, screen, progress_percentage: Optional[float] = None, color: tuple = (0, 229, 179), position: Optional[Union[pygame.Vector2, tuple]] = None, offset: Optional[Union[pygame.Vector2, tuple]] = None):
        """
        Renders the progress bar.

        Args:
        - screen: The screen to render on.
        - progress_percentage (float, optional): The progress percentage. Defaults to None.
        - color (tuple, optional): The color of the progress bar. Defaults to (0, 229, 179).
        - position (pygame.Vector2 or tuple, optional): The position of the progress bar. Defaults to None.
        - offset (pygame.Vector2 or tuple, optional): The offset of the progress bar. Defaults to None.
        """
        if progress_percentage is not None and isinstance(progress_percentage, float):
            self.progress = progress_percentage
        
        bar_rect = pygame.Rect(self.position, (self.length * self.progress, self.thickness))
        if self.is_hovered:
            bar_rect = pygame.Rect(self.position, (self.length * self.progress, self.hover_thickness))
        pygame.draw.rect(screen, color, bar_rect)

    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        """
        Handles mouse events.

        Args:
        - mouse_position (pygame.Vector2): The position of the mouse.
        - new_pressed_button_state: The state of the mouse buttons this frame.
        - held_button_state: The state of the mouse buttons the previous frame.

        Returns:
        - bool: Whether the mouse is hovering over the progress bar.
        """
        relative_mouse_position = pygame.Vector2(mouse_position) - pygame.Vector2(self.position)
        
        # Check if mouse is within the tolerance of the progress bar
        if (-self.drag_tolerance <= relative_mouse_position.x <= self.length + self.drag_tolerance and -self.vert_drag_tolerance <= relative_mouse_position.y <= self.hover_thickness+self.vert_drag_tolerance):
            self.is_hovered = True
            if held_button_state[0]:
                self.progress = min(max(relative_mouse_position[0]/self.length, 0), 1)  # Ensure progress is between 0 and 1
                if self.on_progress_click is not None:
                    self.on_progress_click(self.progress)
        else:
            self.is_hovered = False
        return self.is_hovered
    
    @property
    def progress(self) -> float:
        """
        Gets the progress value.

        Returns:
        - float: The progress value.
        """
        return self._progress

    @progress.setter
    def progress(self, value: float):
        """
        Sets the progress value.

        Args:
        - value (float): The progress value.
        """
        self._progress = min(max(value, 0), 1)


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#


class TextInput:
    """
    A text input widget.

    Attributes:
    - width (int): The width of the text input.
    - vertical_padding (int): The padding above and below the text.
    - position (pygame.Vector2 or tuple): The position of the text input.
    - font (pygame.font.Font): The font to use for rendering the text.
    - background_color (tuple): The background color of the text input.
    - text_color (tuple): The color of the text.
    - on_text_change (Callable[[str], None]): A callback function to be called when the text changes.
    """

    def __init__(self, background_image: pygame.Surface, font: pygame.font.Font, position: Union[pygame.Vector2, tuple] = pygame.Vector2(), edge_padding: int = 4, text_color: tuple = (255, 255, 255)) -> None:
        """
        Initializes a new text input.

        Args:
        - position (pygame.Vector2 or tuple, optional): The position of the text input. Defaults to pygame.Vector2().
        - font (pygame.font.Font, optional): The font to use for rendering the text. Defaults to pygame.font.SysFont("Arial", 24).
        - background_image (pygame.Surface, optional): The image to use as the background. Defaults to None.
        - edge_padding (int, optional): The padding around the edges of the text input. Defaults to 2.
        - text_color (tuple, optional): The color of the text. Defaults to (255, 255, 255).
        """
        self.position = position
        self.font = font
        self.background_image = background_image
        self.edge_padding = edge_padding
        self.text_color = text_color
        self.text = "debug text"
        self.is_focused = False
        self.on_text_change: Callable[[str], None] = None
        self.on_paste: Callable[[str], None] = None
        self.on_enter: Callable[[str], None] = None

        # Calculate the width and height based on the background image
        if not isinstance(self.background_image, pygame.Surface):
            raise ValueError(f"Background image must be a Pygame Surface not {type(self.background_image)}")
        self.width = self.background_image.get_width()
        self.height = self.background_image.get_height()

    def render(self, screen):
        """
        Renders the text input.

        Args:
        - screen: The screen to render on.
        """
        if self.background_image is not None:
            screen.blit(self.background_image, self.position)

        display_text = self.text
        if self.is_focused:
            display_text += "|"
        
        text_surface, _ = self.font.render(display_text, self.text_color)
        if text_surface.get_width() > (self.width-(self.edge_padding)):
            text_surface = pygame.transform.scale(text_surface, (self.width-self.edge_padding, text_surface.get_height()))
        text_rect = text_surface.get_rect(center=(self.position[0] + self.width / 2, self.position[1] + self.height / 2))
        screen.blit(text_surface, text_rect)

    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        """
        Handles mouse events.

        Args:
        - mouse_position (pygame.Vector2): The position of the mouse.
        - new_pressed_button_state: The state of the mouse buttons this frame.
        - held_button_state: The state of the mouse buttons the previous frame.

        Returns:
        - bool: Whether the mouse is hovering over the text input.
        """
        relative_mouse_position = pygame.Vector2(mouse_position) - pygame.Vector2(self.position)
        
        # Check if mouse is within the text input
        if (0 <= relative_mouse_position.x <= self.width and 0 <= relative_mouse_position.y <= self.height):
            if new_pressed_button_state != held_button_state and new_pressed_button_state[0]:#this evaluates to true when you click on this with LMB
                self.is_focused = True
            elif new_pressed_button_state != held_button_state and new_pressed_button_state[2]:  # Right mouse button
                self.text = clipboard.paste()  # Paste the content of the clipboard
                if self.on_paste is not None:
                    self.on_paste(self.text)
            return True
        return False
    
    def handle_key_press(self, key):
        """
        Handles key values given from elsewhere.

        Args:
        - key: The pressed key.
        """
        if self.is_focused:
            if key == pynput.keyboard.Key.backspace:
                self.text = self.text[:-1]
            elif key == pynput.keyboard.Key.enter:
                self.is_focused = False
                if self.on_enter is not None:
                    self.on_enter(self)
            elif key == pynput.keyboard.Key.space:  # Check if the key is the space bar
                self.text += ' '  # Append a space to the text
                if self.on_text_change is not None:
                    self.on_text_change(self)
            else:
                try:
                    self.text += key.char
                    if self.on_text_change is not None:
                        self.on_text_change(self)
                except AttributeError:
                    pass  # Ignore non-character keys


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#


class WidgetImage:
    """
    basic image that is designed to be included in the Node object's children
    """
    def __init__(self,image, position = pygame.Vector2()):
        self.image = image
        self.position = position
    
    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        return False
    def render(self,screen):
        screen.blit(self.image,self.position)


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#

class Node:
    def __init__(self, children=None):
        self.children = []
        if children is not None:
            self.create_children(children)

    def create_children(self, child_list):
        """
        expects a list of lists
        """
        if child_list:
            self.children.extend(child_list[0])
            if len(child_list) > 1:
                self.children.append(Node(child_list[1:]))
    
    def render(self, screen):
        for child in self.children:
            child.render(screen)
    
    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state) -> bool:
        for child in self.children:
            # print(mouse_position)
            if child.handle_mouse(mouse_position,new_pressed_button_state,held_button_state):
                #if the magic function returns true (because the mouse is over it and it's an interactable thing), then stop trying to render in more stuff
                return True
        #if nothing was True, then no interactable elements were found in the children, so return False so that if this is a child you can handle that gracefully.
        return False


#--------------------------------------------------------------------#
#---------------------------- NEW OBJECT ----------------------------#
#--------------------------------------------------------------------#

import cv2
class AudioVisualizer:
    def __init__(self, audio_player, width, height, position:pygame.Vector2 = pygame.Vector2(), line_base_color = (0, 229, 179)):
        self.position = position
        self.width = width
        self.height = height
        self.line_base_color = line_base_color
        self.display_data = None
        self.audio_player = audio_player
        self.display_x = []
        self.display_y = []
        self.audio_chunk_size = 1

    def update_audio_display_data(self, audio_data, mode="mono"):
        if audio_data is not None:
            # Stretch the audio data to fit the width of the display
            if mode == "mono":
                self.display_y = (np.mean(audio_data, axis=1) + 1) / 2 * (self.height-1)
            elif mode == "channels":
                num_channels = audio_data.shape[1]
                channel_height = (self.height-1) / num_channels
                y = []
                for i in range(num_channels):
                    y.append((audio_data[:, i] + 1) / 2 * channel_height + i * channel_height)
                self.display_y = np.array(y).T
            else:
                print("Unexpected mode:", mode)
                self.display_y = (np.mean(audio_data, axis=1) + 1) / 2 * (self.height-1)
            # self.display_x = np.linspace(self.position[0], self.width + self.position[0], len(audio_data))
            self.display_x = np.linspace(0, self.width-1, len(audio_data))

    def render(self,screen):
        if len(self.display_x)*len(self.display_y) > 0:
            # Create a 3D NumPy array to store the pixel data
            pixel_data = np.zeros((self.width, self.height, 3), dtype=np.uint8)

            # Draw the points onto the pixel data
            def stack_columns(col):
                pixel_data[np.clip(np.int_(self.display_x), 0, self.width-1), np.clip(np.int_(col),0,self.height-1)] = self.line_base_color
            np.apply_along_axis(stack_columns, 0, self.display_y)

            # Convert the pixel data to a cv2 image
            image = cv2.cvtColor(pixel_data, cv2.COLOR_RGB2BGR)

            # Convert the cv2 image to a Pygame Surface
            surf = pygame.surfarray.make_surface(image)

            # Blit the Surface onto the screen
            screen.blit(surf, self.position)
        
    def handle_mouse(self, mouse_position: pygame.Vector2, new_pressed_button_state, held_button_state):
        return False
