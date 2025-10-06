import os
import json
import random
import subprocess
import string
import re
import argparse
import logging
import time

from sys import exit
from typing import Tuple, List, Union
from logging.handlers import RotatingFileHandler

path = os.path.join(os.path.expanduser('~'), ".config", "input-simulation")
os.makedirs(path, exist_ok=True)

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception as e:
    import traceback
    import datetime

    error_file = os.path.join(path, "error_input-simulation.log")
    with open(error_file, "a") as file:
        file.write("Date and time: \n")
        file.write(str(datetime.datetime.now()))
        file.write("\n\n")
        file.write("Error: \n")
        file.write("¿Maybe this computer has no graphical interface? Check the error below: \n")
        file.write(str(e))
        file.write("\n\n")
        file.write("Traceback: \n")
        file.write(str(traceback.format_exc()))
        file.write("\n\n")
        file.write("Environment variables: \n")
        file.write(str(os.environ))
        file.write("\n\n")
    exit(1)


format_str = "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(format_str)
logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)



example = """
example:
  move             mouse "100,200" or mouse "M,100,200"
  move relative    mouse "+50,-30" (50 right, 30 up from current position)
  move on image    mouse "/path/to/image.png" or mouse "M,/path/to/image.png"
  single click     mouse "L,100,200"
  double click     mouse "LL,100,200"
  right click      mouse "R,100,200"
  middle click     mouse "W,100,200"
  click on image   mouse "L,/path/to/image.png"
  click current    mouse "L" or click "R" or click "M" or click "LL"
  click relative   mouse "L,+50,-30" (50 right, 30 up from current position)
  sleep            mouse "S,2.5" (sleeps 2.5 seconds)
  multiple clicks  mouse "L,100,200 R,/path/to/image.png S,1 L,+50,-30 LL" (sequence of actions)
"""

def mouse_cmd(
        actions: Tuple[str, Tuple],
        sleep_time: float=0.0,
        duration: float=0.0,
        doubleclick_interval: float=0.1
    ):
    """Simulate a sequence of mouse movements and clicks, whether on coordinates or on images located on the screen."""
    logger.debug(f"Starting mouse_cmd with actions: {actions}, sleep_time: {sleep_time}, duration: {duration}, doubleclick_interval: {doubleclick_interval}")
    btn_mapping = {
        "LL": pyautogui.LEFT,
        "L": pyautogui.LEFT, 
        "R": pyautogui.RIGHT, 
        "W": pyautogui.MIDDLE
    }
    tweening_functions = [
        pyautogui.easeInOutCirc,
        pyautogui.easeOutBack
    ]

    for action, args in actions:
        logger.debug(f"Processing action: {action} with args: {args}")
        if action == "S":  # Sleep
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
                location = pyautogui.locateCenterOnScreen(img_path, confidence=0.8, grayscale=True)
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

            if duration > 0.0 or action == "M":  # Move mouse
                logger.debug(f"Moving mouse to ({x}, {y}) with duration {duration} seconds")
                pyautogui.moveTo(x, y, tween=random.choice(tweening_functions), duration=duration)
            
            if action != "M":  # Not just moving
                btn_mapped = btn_mapping[action]  # Map button to pyautogui constant
                single_click = action != "LL"
                clicks = 1 if single_click else 2
                interval = 0.0 if single_click else doubleclick_interval
                msg = "Clicked" if single_click else "Double clicked"

                pyautogui.click(x, y, button=btn_mapped, clicks=clicks, interval=interval)
                logger.debug(f"{msg} {btn_mapped} button on ({x}, {y})")

                if sleep_time > 0.0:
                    logger.debug(f"Waiting {sleep_time} seconds after the click.")
                    time.sleep(sleep_time)


def validate_mouse_action(action: str) -> str:
    """Validates a click action string and returns with the action in uppercase."""
    if (action_validated := action.upper()) in ["L", "R", "W", "LL", "M", "S"]:
        return action_validated
    else:
        raise ValueError(f"Invalid action '{action}'. Use L, R, W, LL, M or S.")
    

def validate_img_path(img_path: str) -> str:
    """Validates if a path is a valid image file path and returns the absolute path."""
    img_path = os.path.abspath(os.path.expanduser(img_path))
    if not os.path.isfile(img_path):
        raise ValueError(f"Image file '{img_path}' does not exist.")
    return img_path
    

def check_coordinate_format(coord: str) -> bool:
    """Checks if a value is a valid coordinate (integer or relative integer)."""
    return coord.isdigit() or ((coord.startswith("+") or coord.startswith("-")) and coord[1:].isdigit())
    

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


def parse_mouse_actions(actions_str: str) -> List[Tuple[str, Tuple]]:
    """Converts a string of actions into a list of tuples with action and arguments."""
    logger.debug(f"Parsing actions: {actions_str}")
    actions = []
    action_tuples = actions_str.split()
    for action_tuple in action_tuples:
        try:
            parts = action_tuple.split(',')
            # If action has 1 part, it must be one of:
            # - btn -> click current position
            # - image_path -> move to image
            if len(parts) == 1:
                # action = validate_mouse_action(parts[0])
                # args = tuple()
                if parts[0] in ["L", "R", "W", "LL"]:  # Click current position
                    action = validate_mouse_action(parts[0])
                    args = tuple()
                else:  # Move to image
                    action = "M"
                    args = (validate_img_path(parts[0]),)
            # If action has 2 parts, it must be one of:
            # - S,seconds -> sleep
            # - x,y -> left click
            # - btn,image_path -> click on image
            elif len(parts) == 2:
                if parts[0].upper() == "S":  # Sleep
                    action = "S"
                    if (seconds := float(parts[1])) < 0.0:
                        raise ValueError("Sleep time cannot be negative.")
                    args = (seconds,)
                elif check_coordinate_format(parts[0]):  # x,y coordinates
                    action = "M"
                    args = validate_coordinates(parts[0], parts[1])
                else:
                    action = validate_mouse_action(parts[0])
                    args = (validate_img_path(parts[1]),)
            # If action has 3 parts, it must be btn,x,y or M,x,y
            elif len(parts) == 3:
                btn, x, y = parts
                action = validate_mouse_action(btn)
                args = validate_coordinates(x, y)
            else:
                raise ValueError(f"The action has more than 3 parts separated by commas.")
            logger.debug(f"Parts: {parts} to -> action: {action}, args: {args}")
            actions.append((action, args))
        except ValueError as e:
            logger.error(f"Invalid format for action {action_tuple}: {e}")
            exit(1)
    return actions


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
        epilog=example, 
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mouse_parser.add_argument("actions", type=str, help="The sequence of actions to follow: clicks and sleeps. "
                              "An item in the sequence represents a click on coordinates or to sleep by some amount of seconds. "
                              "If clicking, it can be in the format: {btn,}x,y or {btn,}image_path if single click, "
                              "or a list in the format '{btn,}x,y {btn,}image_path {btn,}x,y' if multiple clicks (always in single or double quotes). "
                              "btn is optional, it defaults to left click, and can be L (left), R (right), M (middle) or LL (left double click). "
                              "image_path is the path to an image file to locate on the screen. "
                              "If sleeping, it can be in the format: S,seconds, where seconds is a float number of seconds to sleep. "
                              "Global sleep time between actions can be set with --sleep. "
                              "Coordinates in x,y and image_path can be used in the same sequence, as well as sleeping. ")
    mouse_parser.add_argument("--sleep", type=float, help="Time in seconds (float) to sleep after each click. If sleep is used in actions, it overrides this argument. Defaults to 0.0s", default=0.0, required=False)
    mouse_parser.add_argument("--doubleclick-interval", type=float, help="Time in seconds (float) between clicks for a double click. Defaults to 0.1s.", default=0.1, required=False)
    mouse_parser.add_argument("--duration", type=float, help="Time in seconds (float) to move the mouse to the given coordinates. Defaults to 0.0s", default=0.0, required=False)
    mouse_parser.add_argument("--confidence", type=float, help="Confidence level (0.0 to 1.0) for image recognition. Defaults to 0.8.", default=0.8, required=False)
    mouse_parser.add_argument("--grayscale", action="store_true", help="Use grayscale for image recognition. This is the default option.", default=True, required=False)
    mouse_parser.add_argument("--no-grayscale", action="store_false", dest="grayscale", help="Do not use grayscale for image recognition.", required=False)
    mouse_parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False)

    # Keyboard command (not implemented yet)

    args, unknown = parser.parse_known_args()

    file_handler = RotatingFileHandler(
        os.path.join(os.path.expanduser(path), 'input-simulation.log'),
        maxBytes=1024*1024, 
        backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    if args.debug:
        logger.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    logger.info("Starting input-simulation")
    if unknown:
        logger.warning(f"Unknown arguments ignored: {unknown}")

    if args.command == "mouse":
        mouse_actions = parse_mouse_actions(args.actions)
        mouse_cmd(mouse_actions, args.sleep, args.duration, args.doubleclick_interval)
    else:
        logger.error("Invalid command")
        exit(1)

    logger.info("Finishing input-simulation")

if __name__ == "__main__":
    main()
