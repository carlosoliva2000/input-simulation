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
from typing import Tuple, List
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


format_str = '%(asctime)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(format_str)
logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)



example = """
example:
  single click     clicker.py 150,200
  multiple clicks  clicker.py 150,200 400,500 200,100
"""

def click(coordinates: Tuple[int, int], sleep_time: float=0.0):
    for x, y in coordinates:
        pyautogui.click(x, y)
        logger.debug(f"Clicked on ({x}, {y})")
        if sleep_time > 0.0:
            logger.debug(f"Waiting {sleep_time} seconds after the click.")
            time.sleep(sleep_time)


def parse_coordinates(coord_str: str) -> List[Tuple[int, int]]:
    """Converts a coordinate string into a list of (x, y) tuples"""
    logger.debug(f"Parsing coordinates: {coord_str}")
    coordinates = []
    coord_pairs = coord_str.split()
    for pair in coord_pairs:
        try:
            x, y = map(int, pair.split(','))
            coordinates.append((x, y))
        except ValueError:
            logger.error(f"Invalid format for coordinates {pair}")
            exit(1)
    return coordinates


def main():
    parser = argparse.ArgumentParser(
        prog="input-simulation",
        description="Simulate input such as clicking, moving the mouse or typing", 
        epilog=example, 
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command to execute')

    # Click command
    click_parser = subparsers.add_parser(
        "click", 
        help="Simulate a click", 
        epilog=example, 
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    click_parser.add_argument("coordinates", type=str, help="Coordinates in the format 'x,y' o 'x y' if single click, or a list in the format 'x,y x,y x,y' if multiple clicks.")
    click_parser.add_argument("--sleep", type=float, help="Time in seconds (float) to sleep after each click.", default=0.0, required=False)
    click_parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False)

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

    if args.command == "click":
        coordinates = parse_coordinates(args.coordinates)
        click(coordinates, args.sleep)
    else:
        logger.error("Invalid command")
        exit(1)

if __name__ == "__main__":
    main()
