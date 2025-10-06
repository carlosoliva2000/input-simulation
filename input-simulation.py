import os
import random
import subprocess
import pyperclip
import argparse
import logging
import time
import shlex
import enum

from sys import exit
from typing import Tuple, List, Union
from filelock import FileLock
from logging.handlers import RotatingFileHandler


LOCK = FileLock(os.path.join("/", "opt", "scripts", ".gui.lock"))
LOG_PATH = os.path.join(os.path.expanduser('~'), ".config", "input-simulation")
os.makedirs(LOG_PATH, exist_ok=True)

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception as e:
    import traceback
    import datetime

    error_file = os.path.join(LOG_PATH, "error_input-simulation.log")
    with open(error_file, "a") as file:
        file.write("Date and time: \n")
        file.write(str(datetime.datetime.now()))
        file.write("\n\n")
        file.write("Error: \n")
        file.write("Maybe this computer has no graphical interface? Check the error below: \n")
        file.write(str(e))
        file.write("\n\n")
        file.write("Traceback: \n")
        file.write(str(traceback.format_exc()))
        file.write("\n\n")
        file.write("Environment variables: \n")
        file.write(str(os.environ))
        file.write("\n\n")
    exit(1)



# Constants - Default

MIN_TYPING_INTERVAL = 0.025  # Minimum interval between typed characters to avoid issues with some systems
RECOMMENDED_TYPING_INTERVAL = 0.05  # Recommended interval between typed characters to avoid issues with some systems
DEFAULT_SLEEP_TIME = 0.0  # Default sleep time between actions
DEFAULT_DURATION = 0.0  # Default duration for mouse movements
DEFAULT_DOUBLECLICK_INTERVAL = 0.1  # Default interval between clicks for double click
DEFAULT_CONFIDENCE = 0.8  # Default confidence for image recognition
DEFAULT_GRAYSCALE = True  # Default to use grayscale for image recognition
DEFAULT_TYPING_INTERVAL = RECOMMENDED_TYPING_INTERVAL  # Default interval between typed characters
DEFAULT_PRESS_INTERVAL = 0.0  # Default interval between key presses when pressing multiple times



# Enums

class ActionType(str, enum.Enum):
    MOUSE = "MOUSE"
    KEYBOARD = "KEYBOARD"

class MouseAction(str, enum.Enum):
    SLEEP = "SLEEP"
    S = "S"
    LEFT = "LEFT"
    L = "L"
    RIGHT = "RIGHT"
    R = "R"
    MIDDLE = "MIDDLE"
    W = "W"
    DOUBLELEFT = "DOUBLELEFT"
    LL = "LL"
    MOVE = "MOVE"
    M = "M"

class KeyboardAction(str, enum.Enum):
    SLEEP = "SLEEP"
    S = "S"
    KEY = "KEY"
    K = "K"
    TYPE = "TYPE"
    T = "T"
    TYPEFILE = "TYPEFILE"
    TF = "TF"



# Constants - Other

MOUSE_ACTIONS_DICT = {
    MouseAction.L: MouseAction.LEFT,
    MouseAction.R: MouseAction.RIGHT,
    MouseAction.W: MouseAction.MIDDLE,
    MouseAction.LL: MouseAction.DOUBLELEFT,
    MouseAction.M: MouseAction.MOVE,
    MouseAction.S: MouseAction.SLEEP
}
MOUSE_ACTIONS_LIST = list(MOUSE_ACTIONS_DICT.keys()) + list(MOUSE_ACTIONS_DICT.values())
MOUSE_ACTIONS_STR = ', '.join(MOUSE_ACTIONS_LIST)
MOUSE_CLICK_ACTIONS_LIST = [action for action in MOUSE_ACTIONS_LIST if action not in [MouseAction.M, MouseAction.MOVE, MouseAction.S, MouseAction.SLEEP]]
MOUSE_SLEEP_ACTIONS_LIST = [MouseAction.S, MouseAction.SLEEP]

KEYBOARD_ACTIONS_LIST = [
    KeyboardAction.KEY, 
    KeyboardAction.K, 
    KeyboardAction.TYPE, 
    KeyboardAction.T, 
    KeyboardAction.TYPEFILE, 
    KeyboardAction.TF, 
    KeyboardAction.SLEEP, 
    KeyboardAction.S
]
KEYBOARD_ACTIONS_STR = ', '.join(KEYBOARD_ACTIONS_LIST)
KEYBOARD_SLEEP_ACTIONS_LIST = [KeyboardAction.S, KeyboardAction.SLEEP]
KEYBOARD_KEY_ACTIONS_LIST = [KeyboardAction.K, KeyboardAction.KEY]
KEYBOARD_TYPE_ACTIONS_LIST = [KeyboardAction.T, KeyboardAction.TYPE]
KEYBOARD_TYPEFILE_ACTIONS_LIST = [KeyboardAction.TF, KeyboardAction.TYPEFILE]

BTN_MAPPING = {
    MouseAction.DOUBLELEFT: pyautogui.LEFT,
    MouseAction.LEFT: pyautogui.LEFT, 
    MouseAction.RIGHT: pyautogui.RIGHT, 
    MouseAction.MIDDLE: pyautogui.MIDDLE
}

TWEENING_FUNCTIONS = [
    pyautogui.easeInOutCirc,
    pyautogui.easeOutBack
]

PROBLEMATIC_CHARS = set("@|#$%&/()=?¡¿'\"\\[]{}^`~¬¨*+-_:;<>")



# Logging setup

format_str = "%(asctime)s [PID %(process)d] - %(funcName)s - %(levelname)s - %(message)s"
class LevelBasedFormatter(logging.Formatter):
    """Custom formatter to change format based on log level."""
    def format(self, record):
        if record.levelno == logging.INFO:
            fmt = "%(message)s"
        else:
            fmt = format_str
        formatter = logging.Formatter(fmt)
        return formatter.format(record)


formatter = logging.Formatter(format_str)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(
    os.path.join(os.path.expanduser(LOG_PATH), 'input-simulation.log'),
    maxBytes=1024*1024, 
    backupCount=3
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



# Examples for help messages

example_mouse = """
example:
  move                  mouse "100,200" or mouse "M,100,200" or mouse "MOVE,100,200"
  move relative         mouse "+50,-30" (50 right, 30 up from current position) (use +0 when you want to move only in one axis)
  move on image         mouse "/path/to/image.png" or mouse "M,/path/to/image.png" or mouse "MOVE,/path/to/image.png"
  single click          mouse "L,100,200" or mouse "LEFT,100,200"
  double click          mouse "LL,100,200" or mouse "DOUBLELEFT,100,200"
  right click           mouse "R,100,200" or mouse "RIGHT,100,200"
  middle click          mouse "W,100,200" or mouse "MIDDLE,100,200"
  click on image        mouse "L,/path/to/image.png"
  click current         mouse "L" or click "R" or click "M" or click "LL" (or their full names)
  click relative        mouse "L,+50,-30" (50 right, 30 up from current position) (use +0 when you want to move only in one axis)
  sleep                 mouse "S,2.5" or mouse "SLEEP,2.5" (sleeps 2.5 seconds)
  multiple actions      mouse "100,200 R S,0.5 L,/path/to/image.png L,+50,-30" (sequence of actions)
"""

example_keyboard = """
example:
  press key             keyboard "K,Enter" or keyboard "KEY,Enter"
  press hotkey          keyboard "K,ctrl+shift+c" or keyboard "KEY,ctrl+shift+c" (case insensitive)
  press multiple        keyboard "K,Enter,3" or keyboard "KEY,Enter,3" (presses Enter 3 times) (works with hotkeys too)
  type (string)         keyboard "T,'Hello World'" or keyboard "TYPE,'Hello World'" (with quotes)
  type (file)           keyboard "TF,/path/to/file.txt" or keyboard "TYPEFILE,/path/to/file.txt" (types the content of the file) (use quotes if path has spaces)
  sleep                 keyboard "S,2.5" or keyboard "SLEEP,2.5" (sleeps 2.5 seconds)
  multiple actions      keyboard "S,1.5 T,'Hello World' K,Enter,2 T,/path/content.txt K,Ctrl+S" (sequence of actions, with quotes for strings when typing)
"""

example_input = """
example:
  mouse and keyboard    input "100,200 R S,0.5 L,/path/to/image.png T,'Hello World' K,Enter,2 T,/path/content.txt K,Ctrl+S"
  (sequence of mouse and keyboard actions, with quotes for strings when typing)
  (see the help of mouse and keyboard commands for the format of each action and more examples)
"""



# Auxiliary functions (typing, validations, checks)

def type_with_xdotool_single(text):
    subprocess.run(["xdotool", "type", "--clearmodifiers", text])


def type_text(text, interval=MIN_TYPING_INTERVAL):
    """DEPRECATED: this function is very slow.

    Type text using pyautogui, handling problematic characters with xdotool."""
    buffer = ""

    def flush_buffer():
        nonlocal buffer
        if buffer:
            pyautogui.write(buffer, interval=interval)
            buffer = ""

    for ch in text:
        if ch in PROBLEMATIC_CHARS or ord(ch) > 126:
            # First, write the buffer if not empty
            flush_buffer()
            # Paste the problematic character using xdotool
            type_with_xdotool_single(ch)
        else:
            buffer += ch

    flush_buffer()


def type_with_xdotool(text: str, interval=MIN_TYPING_INTERVAL):
    if interval < MIN_TYPING_INTERVAL:
        logger.debug(f"Interval {interval} too low, typing whole text at once.")
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        lines = text.splitlines(keepends=True)
        interval = str(interval * 1000)  # Convert to milliseconds for xdotool
        for line in lines:
            if line.endswith('\n'):
                subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", interval, line[:-1]])
                subprocess.run(["xdotool", "key", "Return"])
            else:
                subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", interval, line])


def validate_mouse_action(action: str) -> str:
    """Validates a click action string and returns with the action in uppercase."""
    if (action_validated := action.upper()) in MOUSE_ACTIONS_LIST:
        return MOUSE_ACTIONS_DICT.get(action_validated, action_validated)
    else:
        raise ValueError(f"Invalid action '{action}'. Use {MOUSE_ACTIONS_STR}.")
    

def validate_keyboard_action(action: str) -> str:
    """Validates a keyboard action string and returns with the action in uppercase."""
    if (action_validated := action.upper()) in KEYBOARD_ACTIONS_LIST:
        return action_validated
    else:
        raise ValueError(f"Invalid action '{action}'. Use {KEYBOARD_ACTIONS_STR}.")
    

def validate_file_path(path: str, directory: Union[str, None]=None) -> str:
    """Validates if a path is a valid file path and returns the absolute path."""
    logger.debug(f"Validating file path: {path} with directory: {directory}")
    if directory:
        directory = os.path.abspath(os.path.expanduser(directory))
        path = os.path.join(directory, path)
    else:
        path = os.path.abspath(os.path.expanduser(path))
    
    if not os.path.isfile(path):
        raise ValueError(f"File '{path}' does not exist.")
    return path
    

def validate_coordinate(coord: str) -> Union[int, str]:
    """Checks if a value is a valid coordinate (integer or relative integer) and returns them as integers if they are absolute or strings if they are relative."""
    if coord.isdigit():
        return int(coord)
    elif (coord.startswith("+") or coord.startswith("-")) and coord[1:].isdigit():
        return coord
    raise ValueError(f"Invalid coordinate '{coord}'. It must be an integer (absolute or relative).")
    

def validate_coordinates(x: str, y: str) -> Tuple:
    """Validates if x and y are integers (absolute or relative) and returns them as integers if they are absolute or strings if they are relative."""
    return validate_coordinate(x), validate_coordinate(y)


def check_coordinate_format(coord: str) -> bool:
    """Checks if a value is a valid coordinate (integer or relative integer)."""
    return coord.isdigit() or ((coord.startswith("+") or coord.startswith("-")) and coord[1:].isdigit())


def check_mouse_args(args) -> bool:
    """Check if the arguments for mouse command are valid."""
    if args.doubleclick_interval < 0.0:
        logger.error("Double click interval cannot be negative.")
        return False
    if args.duration < 0.0:
        logger.error("Duration cannot be negative.")
        return False
    if not (0.0 <= args.confidence <= 1.0):
        logger.error("Confidence must be between 0.0 and 1.0.")
        return False
    return True


def check_keyboard_args(args) -> bool:
    """Check if the arguments for keyboard command are valid."""
    if args.typing_interval < 0.0:
        logger.error("Typing interval cannot be negative.")
        return False
    if args.typing_interval < MIN_TYPING_INTERVAL:
        logger.warning(f"Typing interval too low (less than {MIN_TYPING_INTERVAL}s). Setting to type the whole string at once.")
    if args.press_interval < 0.0:
        logger.error("Press interval cannot be negative.")
        return False
    return True



# Parsers

def parse_mouse_actions(
    actions_str: str,
    images_path: Union[str, None]=None
) -> List[Tuple[str, Tuple]]:
    """Converts a string of mouse actions into a list of tuples with action and arguments."""
    logger.debug(f"Parsing mouse actions: {actions_str}")
    actions = []
    action_tuples = actions_str.split()
    for action_tuple in action_tuples:
        logger.debug(f"Processing item: {action_tuple}")
        try:
            parts = action_tuple.split(',')
            # If action has 1 part, it must be one of:
            # - btn -> click current position
            # - image_path -> move to image
            if len(parts) == 1:
                # action = validate_mouse_action(parts[0])
                # args = tuple()
                if parts[0] in MOUSE_CLICK_ACTIONS_LIST:  # Click current position
                    action = validate_mouse_action(parts[0])
                    args = tuple()
                else:  # Move to image
                    action = MouseAction.MOVE
                    args = (validate_file_path(parts[0], images_path),)
            # If action has 2 parts, it must be one of:
            # - S,seconds -> sleep
            # - x,y -> left click
            # - btn,image_path -> click on image
            elif len(parts) == 2:
                if parts[0].upper() in MOUSE_SLEEP_ACTIONS_LIST:  # Sleep
                    action = MouseAction.SLEEP
                    if (seconds := float(parts[1])) < 0.0:
                        raise ValueError("Sleep time cannot be negative.")
                    args = (seconds,)
                elif check_coordinate_format(parts[0]):  # x,y coordinates
                    action = MouseAction.MOVE
                    args = validate_coordinates(parts[0], parts[1])
                else:
                    action = validate_mouse_action(parts[0])
                    args = (validate_file_path(parts[1], images_path),)
            # If action has 3 parts, it must be btn,x,y or M,x,y
            elif len(parts) == 3:
                btn, x, y = parts
                action = validate_mouse_action(btn)
                args = validate_coordinates(x, y)
            else:
                raise ValueError(f"The action has more than 3 parts separated by commas.")
            logger.debug(f"Item: {parts} to -> action: {action}, args: {args}")
            actions.append((action, args))
        except ValueError as e:
            logger.error(f"Invalid format for action {action_tuple}: {e}")
            exit(1)
    return actions


def parse_keyboard_actions(
    actions_str: str, 
    files_path: Union[str, None]=None,
    from_input=False
) -> List[Tuple[str, Union[str, Tuple]]]:
    """Converts a string of keyboard actions into a list of tuples with action and arguments."""
    logger.debug(f"Parsing keyboard actions: {actions_str}")
    actions = []

    if not from_input:
        actions_split = shlex.split(actions_str)  # To handle quoted strings with spaces
    else:
        actions_split = [actions_str]  # When called from input command, the whole string is one action
    
    for item in actions_split:
        try:
            logger.debug(f"Processing item: {item}")
            res = item.split(",", 1)  # Split by comma except the first part
            action = res[0]
            args = res[1]

            if action.upper() in KEYBOARD_SLEEP_ACTIONS_LIST:  # Sleep
                action = KeyboardAction.SLEEP
                if (seconds := float(args)) < 0.0:
                    raise ValueError("Sleep time cannot be negative.")
                args = (seconds,)
            elif action.upper() in KEYBOARD_KEY_ACTIONS_LIST:
                args = args.split(",")
                keys = args[0].lower().split('+')
                presses = 1 if len(args) == 1 else int(args[1])
                action = KeyboardAction.KEY
                args = (keys, presses)
            elif action.upper() in KEYBOARD_TYPE_ACTIONS_LIST:
                action = KeyboardAction.TYPE
                args = (args,)
            elif action.upper() in KEYBOARD_TYPEFILE_ACTIONS_LIST:
                action = KeyboardAction.TYPEFILE
                args = (validate_file_path(args, files_path),)
            else:
                raise ValueError(f"Invalid action '{action}'. Use {KEYBOARD_ACTIONS_STR}.")

            logger.debug(f"Item: {item} to -> action: {action}, args: {args}")
            actions.append((action, args))
        except ValueError as e:
            logger.error(f"Invalid format for action {item}: {e}")
            exit(1)
    return actions


def parse_input_actions(
    actions_str: str,
    images_path: Union[str, None]=None,
    files_path: Union[str, None]=None
) -> List[Tuple[str, Union[str, Tuple]]]:
    """Converts a string of mixed mouse and keyboard actions into a list of tuples with action type and action."""
    logger.debug(f"Parsing input actions: {actions_str}")
    combined_actions = []
    actions_split = shlex.split(actions_str)

    # logger.debug(f"Actions split: {actions_split}")
    for item in actions_split:
        try:
            logger.debug(f"Processing item: {item}")
            item_split = item.split(",", 1)
            if len(item_split) == 1 or item_split[0].upper() in MOUSE_ACTIONS_LIST:
                mouse_action = parse_mouse_actions(item, images_path=images_path)
                combined_actions.append((ActionType.MOUSE, mouse_action))
            elif item.split(",", 1)[0].upper() in KEYBOARD_ACTIONS_LIST:
                keyboard_action = parse_keyboard_actions(item, files_path=files_path, from_input=True)
                combined_actions.append((ActionType.KEYBOARD, keyboard_action))
            else:
                raise ValueError("Unknow action. Use mouse or keyboard actions.")
        except ValueError as e:
            logger.error(f"Invalid format for action {item}: {e}")
            exit(1)
    return combined_actions



# Command functions

@LOCK
def mouse_cmd(
    actions: Tuple[str, Tuple],
    sleep_time: float=DEFAULT_SLEEP_TIME,
    duration: float=DEFAULT_DURATION,
    doubleclick_interval: float=DEFAULT_DOUBLECLICK_INTERVAL,
    confidence: float=DEFAULT_CONFIDENCE,
    grayscale: bool=DEFAULT_GRAYSCALE
):
    """Simulate a sequence of mouse movements and clicks, whether on coordinates or on images located on the screen."""
    logger.debug(f"Starting mouse_cmd with actions: {actions}. Args: sleep_time={sleep_time}, duration={duration}, doubleclick_interval={doubleclick_interval}, confidence={confidence}, grayscale={grayscale}")

    for i, (action, args) in enumerate(actions):
        logger.debug(f"Processing action: {action} with args: {args}")
        if action == MouseAction.SLEEP:  # Sleep
            seconds = args[0]
            if seconds > 0.0:
                logger.debug(f"Sleeping for {seconds} seconds (overriding global sleep time of {sleep_time} seconds).")
                time.sleep(seconds)
        else:
            if len(args) == 0:  # Click on current mouse position
                x, y = pyautogui.position()
            elif len(args) == 1:  # Click on image
                img_path = args[0]
                logger.debug(f"Locating image on screen: {img_path}")
                location = pyautogui.locateCenterOnScreen(img_path, confidence=confidence, grayscale=grayscale)
                if location is None:
                    logger.error(f"Image '{img_path}' not found on screen.")
                    exit(1)
                x, y = location
                logger.debug(f"Image found at ({x}, {y})")
            elif len(args) == 2:  # Click on coordinates
                x, y = args
                cur_pos = pyautogui.position()
                x = x if isinstance(x, int) else cur_pos.x + int(x)
                y = y if isinstance(y, int) else cur_pos.y + int(y)

            if duration > 0.0 or action == MouseAction.MOVE:  # Move mouse
                logger.debug(f"Moving mouse to ({x}, {y}) with duration {duration} seconds")
                pyautogui.moveTo(x, y, tween=random.choice(TWEENING_FUNCTIONS), duration=duration)
            
            if action != MouseAction.MOVE:  # Not just moving
                btn_mapped = BTN_MAPPING[action]  # Map button to pyautogui constant
                single_click = action != MouseAction.DOUBLELEFT
                clicks = 1 if single_click else 2
                interval = 0.0 if single_click else doubleclick_interval
                msg = "Clicked" if single_click else "Double clicked"

                pyautogui.click(x, y, button=btn_mapped, clicks=clicks, interval=interval)
                logger.debug(f"{msg} {btn_mapped} button on ({x}, {y})")

            if sleep_time > 0.0 and i < len(actions) - 1:  # No sleep after the last action
                logger.debug(f"Waiting {sleep_time} seconds after the mouse action.")
                time.sleep(sleep_time)


@LOCK
def keyboard_cmd(
    actions: Tuple[str, Union[str, Tuple]],
    sleep_time: float=DEFAULT_SLEEP_TIME,
    typing_interval: float=DEFAULT_TYPING_INTERVAL,
    press_interval: float=DEFAULT_PRESS_INTERVAL
):
    """Simulate a sequence of keyboard key presses and typing."""
    logger.debug(f"Starting keyboard_cmd with actions: {actions}. Args: sleep_time={sleep_time}, typing_interval={typing_interval}, press_interval={press_interval}")

    for i, (action, args) in enumerate(actions):
        logger.debug(f"Processing action: {action} with args: {args}")
        if action == KeyboardAction.SLEEP:  # Sleep
            seconds = args[0]
            if seconds > 0.0:
                logger.debug(f"Sleeping for {seconds} seconds (overriding global sleep time of {sleep_time} seconds).")
                time.sleep(seconds)
        else:
            if action == KeyboardAction.KEY:  # Key press or combination
                keys = args[0]
                presses = args[1]
                if len(keys) == 1:
                    key = keys[0]
                    logger.debug(f"Pressing key {key} {presses} times with interval {press_interval} seconds between presses")
                    pyautogui.press(key, presses=presses, interval=press_interval)
                else:
                    logger.debug(f"Pressing key combination {keys} {presses} times with interval {press_interval} seconds between presses")
                    for _ in range(presses):
                        pyautogui.hotkey(*keys)
                        if press_interval > 0.0:
                            time.sleep(press_interval)
            elif action == KeyboardAction.TYPE:  # Type string
                string_to_type = args[0]
                logger.debug(f"Typing string: {string_to_type} with interval {typing_interval} seconds between characters")
                type_with_xdotool(string_to_type, interval=typing_interval)
                # pyautogui.write(string_to_type, interval=typing_interval)
            elif action == KeyboardAction.TYPEFILE:  # Type content of file
                file_path = args[0]
                logger.debug(f"Typing content of file: {file_path} with interval {typing_interval} seconds between characters")
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                    type_with_xdotool(content, interval=typing_interval)
                except OSError as e:
                    logger.error(f"Error reading file '{file_path}': {e}")
                    exit(1)
            else:
                logger.error(f"Unknown action '{action}' in keyboard_cmd.")
                exit(1)
            
            if sleep_time > 0.0 and i < len(actions) - 1:  # No sleep after the last action
                logger.debug(f"Waiting {sleep_time} seconds after the keyboard action.")
                time.sleep(sleep_time)


@LOCK
def input_cmd(
    actions: List[Tuple[str, Union[str, Tuple]]],
    sleep_time: float=DEFAULT_SLEEP_TIME,
    duration: float=DEFAULT_DURATION,
    doubleclick_interval: float=DEFAULT_DOUBLECLICK_INTERVAL,
    confidence: float=DEFAULT_CONFIDENCE,
    grayscale: bool=DEFAULT_GRAYSCALE,
    typing_interval: float=DEFAULT_TYPING_INTERVAL,
    press_interval: float=DEFAULT_PRESS_INTERVAL
):
    """Simulate a sequence of mouse and keyboard actions."""
    logger.debug(f"Starting input_cmd with actions: {actions}. Args: sleep_time={sleep_time}, duration={duration}, doubleclick_interval={doubleclick_interval}, confidence={confidence}, grayscale={grayscale}, typing_interval={typing_interval}, press_interval={press_interval}")

    for i, (action_type, action) in enumerate(actions):
        if action_type == ActionType.MOUSE:
            mouse_cmd(action, sleep_time, duration, doubleclick_interval)
        elif action_type == ActionType.KEYBOARD:
            keyboard_cmd(action, sleep_time, typing_interval, press_interval)
        else:
            logger.error(f"Unknown action type '{action_type}' in input_cmd.")
            exit(1)

        is_sleep_action = action[0][0] in (MOUSE_SLEEP_ACTIONS_LIST if action_type == ActionType.MOUSE else KEYBOARD_SLEEP_ACTIONS_LIST)
        if not is_sleep_action and sleep_time > 0.0 and i < len(actions) - 1:  # No sleep after the last action
            logger.debug(f"Waiting {sleep_time} seconds after the last action of type {action_type}.")
            time.sleep(sleep_time)



# Main

def main():
    parser = argparse.ArgumentParser(
        prog="input-simulation",
        description="Simulate input such as clicking, moving the mouse or typing", 
        # epilog=example, 
        # formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command to execute')

    # Mouse command
    mouse_parser = subparsers.add_parser(
        "mouse", 
        help="Simulate a sequence of mouse movements and clicks, whether on coordinates or on images located on the screen.",
        epilog=example_mouse, 
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mouse_parser.add_argument("actions", type=str, help="The sequence of actions to follow: mouse movements, clicks and sleeps. "
                              "An item in the sequence represents a mouse movement, click on coordinates or to sleep by some amount of seconds. "
                              "If moving, it must be in the format: {M,}x,y or {M,}image_path, where M is optional and means move (it defaults to move). "
                              "If clicking, it must be in the format: btn,x,y or btn,image_path if single click, "
                              "or a list in the format 'btn,x,y btn,image_path btn,x,y' if multiple clicks (always in single or double quotes). "
                              "btn can be L (left), R (right), W (middle, wheel button) or LL (left double click). "
                              "image_path is the path to an image file to locate on the screen. "
                              "If sleeping, it must be in the format: S,seconds, where seconds is a float number of seconds to sleep. "
                              "Global sleep time between actions can be set with --sleep. "
                              "Coordinates in x,y and image_path can be used in the same sequence, as well as sleeping. ")
    mouse_parser.add_argument("--sleep", type=float, help="Time in seconds (float) to sleep after each action. If a sleep action is used in the sequence of actions, it overrides this argument. Defaults to 0.0s", default=DEFAULT_SLEEP_TIME, required=False)
    mouse_parser.add_argument("--doubleclick-interval", type=float, help="Time in seconds (float) between clicks for a double click. Defaults to 0.1s.", default=DEFAULT_DOUBLECLICK_INTERVAL, required=False)
    mouse_parser.add_argument("--duration", type=float, help="Time in seconds (float) to move the mouse to the given coordinates. Defaults to 0.0s", default=DEFAULT_DURATION, required=False)
    mouse_parser.add_argument("--confidence", type=float, help="Confidence level (0.0 to 1.0) for image recognition. Defaults to 0.8.", default=DEFAULT_CONFIDENCE, required=False)
    mouse_parser.add_argument("--grayscale", action="store_true", help="Use grayscale for image recognition. This is the default option.", default=DEFAULT_GRAYSCALE, required=False)
    mouse_parser.add_argument("--no-grayscale", action="store_false", dest="grayscale", help="Do not use grayscale for image recognition.", required=False)
    mouse_parser.add_argument("--images-path", type=str, help="Path to a directory where images used for image recognition are stored. If set, image paths in actions can be relative to this path.", default=None, required=False)
    mouse_parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False)

    # Keyboard command
    keyboard_parser = subparsers.add_parser(
        "keyboard", 
        help="Simulate a sequence of pressing keys or hotkeys and typing text.",
        epilog=example_keyboard,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    keyboard_parser.add_argument("actions", type=str, help="The sequence of actions to follow: key presses, typing and sleeps. "
                                  "An item in the sequence represents a key press, a hotkey, a string to type or to sleep by some amount of seconds. "
                                  "If pressing a key or combination of keys, it must be in the format: K,key or K,key,presses if pressing multiple times. "
                                  "key can be a single key or a combination of keys separated by + (e.g., ctrl+shift+c). "
                                  "If typing a string, it must be in the format: T,'string' (always in quotes) or T,/path/to/file.txt if typing the content of a file. "
                                  "If sleeping, it must be in the format: S,seconds, where seconds is a float number of seconds to sleep. "
                                  "Global sleep time between actions can be set with --sleep. "
                                  "Pressing, typing and sleeping can be used in the same sequence.")
    keyboard_parser.add_argument("--sleep", type=float, help="Time in seconds (float) to sleep after each action. If sleep action is used in the sequence of actions, it overrides this argument. Defaults to 0.0s", default=DEFAULT_SLEEP_TIME, required=False)
    keyboard_parser.add_argument("--typing-interval", type=float, help="Time in seconds (float) between each character when typing a string. Defaults to 0.05s. "
                                 "Minimum is 0.025s, lower values will type the whole string at once. "
                                 "Values lower than 0.05s may cause issues on some systems (such as missing characters).", 
                                 default=DEFAULT_TYPING_INTERVAL, required=False)
    keyboard_parser.add_argument("--press-interval", type=float, help="Time in seconds (float) between each key press when pressing keys multiple times. Defaults to 0.0s", default=DEFAULT_PRESS_INTERVAL, required=False)
    keyboard_parser.add_argument("--files-path", type=str, help="Path to a directory where text files used for typing are stored. If set, file paths in actions can be relative to this path.", default=None, required=False)
    keyboard_parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False)

    # Input command (combined mouse and keyboard)
    input_parser = subparsers.add_parser(
        "input", 
        help="Simulate a sequence of mouse and keyboard actions.",
        epilog=example_input,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    input_parser.add_argument("actions", type=str, help="The sequence of actions to follow: mouse movements, clicks, key presses, typing and sleeps. "
                              "See the help of mouse and keyboard commands for the format of each action. ")
    input_parser.add_argument("--sleep", type=float, help="Time in seconds (float) to sleep after each action. If a sleep action is used in the sequence of actions, it overrides this argument. Defaults to 0.0s", default=DEFAULT_SLEEP_TIME, required=False)
    input_parser.add_argument("--doubleclick-interval", type=float, help="Time in seconds (float) between clicks for a double click. Defaults to 0.1s.", default=DEFAULT_DOUBLECLICK_INTERVAL, required=False)
    input_parser.add_argument("--duration", type=float, help="Time in seconds (float) to move the mouse to the given coordinates. Defaults to 0.0s", default=DEFAULT_DURATION, required=False)
    input_parser.add_argument("--confidence", type=float, help="Confidence level (0.0 to 1.0) for image recognition. Defaults to 0.8.", default=DEFAULT_CONFIDENCE, required=False)
    input_parser.add_argument("--grayscale", action="store_true", help="Use grayscale for image recognition. This is the default option.", default=DEFAULT_GRAYSCALE, required=False)
    input_parser.add_argument("--no-grayscale", action="store_false", dest="grayscale", help="Do not use grayscale for image recognition.", required=False)
    input_parser.add_argument("--images-path", type=str, help="Path to a directory where images used for image recognition are stored. If set, image paths in actions can be relative to this path.", default=None, required=False)
    input_parser.add_argument("--typing-interval", type=float, help="Time in seconds (float) between each character when typing a string. Defaults to 0.05s. "
                                 "Minimum is 0.025s, lower values will type the whole string at once. "
                                 "Values lower than 0.05s may cause issues on some systems (such as missing characters).", 
                                 default=DEFAULT_TYPING_INTERVAL, required=False)
    input_parser.add_argument("--press-interval", type=float, help="Time in seconds (float) between each key press when pressing keys multiple times. Defaults to 0.0s", default=DEFAULT_PRESS_INTERVAL, required=False)
    input_parser.add_argument("--files-path", type=str, help="Path to a directory where text files used for typing are stored. If set, file paths in actions can be relative to this path.", default=None, required=False)
    input_parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False)


    args, unknown = parser.parse_known_args()

    if args.debug:
        console_handler.setFormatter(formatter)
    else:
        console_handler.setFormatter(LevelBasedFormatter())
        console_handler.setLevel(logging.INFO)
    
    logger.info("Starting input-simulation")
    if unknown:
        logger.warning(f"Unknown arguments ignored: {unknown}")


    if args.sleep < 0.0:
        logger.error("Sleep time cannot be negative.")
        exit(1)

    if args.command == "mouse":
        if not check_mouse_args(args):
            exit(1)
        mouse_actions = parse_mouse_actions(args.actions, images_path=args.images_path)
        logger.debug(f"Trying to acquire lock on {LOCK.lock_file}")
        mouse_cmd(mouse_actions, args.sleep, args.duration, args.doubleclick_interval)
    elif args.command == "keyboard":
        if not check_keyboard_args(args):
            exit(1)
        keyboard_actions = parse_keyboard_actions(args.actions, files_path=args.files_path)
        logger.debug(f"Trying to acquire lock on {LOCK.lock_file}")
        keyboard_cmd(keyboard_actions, args.sleep, args.typing_interval, args.press_interval)
    elif args.command == "input":
        if not check_mouse_args(args) or not check_keyboard_args(args):
            exit(1)
        combined_actions = parse_input_actions(args.actions, images_path=args.images_path, files_path=args.files_path)
        logger.debug(f"Trying to acquire lock on {LOCK.lock_file}")
        input_cmd(combined_actions, args.sleep, args.duration, args.doubleclick_interval, args.confidence, args.grayscale, args.typing_interval, args.press_interval)
    else:
        logger.error("Invalid command")
        exit(1)
    
    logger.debug(f"Lock released on {LOCK.lock_file}")
    logger.info("Finishing input-simulation")


if __name__ == "__main__":
    main()
