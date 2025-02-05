import sys
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except KeyError:
    print("ERROR: this computer has no graphical interface")
    sys.exit(1)
import argparse
import time
from typing import Tuple, List


example = """
example:
  single click     clicker.py 150,200
  multiple clicks  clicker.py 150,200 400,500 200,100
"""

def click(coordinates: Tuple[int, int], sleep_time: float=0.0):
    for x, y in coordinates:
        pyautogui.click(x, y)
        # print(f"Clic realizado en ({x}, {y})")
        if sleep_time > 0.0:
            time.sleep(sleep_time)
            # print(f"Esperando {sleep_time} segundos después del clic.")

def parse_coordinates(coord_str: str) -> List[Tuple[int, int]]:
    """Converts a coordinate string into a list of (x, y) tuples"""
    coordinates = []
    coord_pairs = coord_str.split()
    for pair in coord_pairs:
        try:
            x, y = map(int, pair.split(','))
            coordinates.append((x, y))
        except ValueError:
            print(f"ERROR: invalid format for coordinates {pair}")
            sys.exit(1)
    return coordinates

def main():
    parser = argparse.ArgumentParser(description="Click on one or multiple coordinates", epilog=example, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("coordinates", type=str, help="coordinates in the format 'x,y' o 'x y' if single click, or a list in the format 'x,y x,y x,y' if multiple clicks")
    parser.add_argument("--sleep", type=float, help="time in seconds (float) to sleep after each click", default=0.0, required=False)

    args = parser.parse_args()

    coordinates = parse_coordinates(args.coordinates)

    click(coordinates, args.sleep)

if __name__ == "__main__":
    main()
