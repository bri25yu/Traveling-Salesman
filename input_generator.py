#!/usr/bin/env python3

import argparse
from random import random, shuffle
from math import floor, sqrt
from decimal import Decimal
from utils import write_to_file

def random_subset(values, count: int):
  ret = []
  while len(ret) < count:
    next_index = floor(random() * len(values))
    ret.append(values[next_index])
    del values[next_index]
  return ret

def generate_names(count: int):
  names = [str(i) for i in range(0, count)]
  shuffle(names)
  return names

def generate_input(locations: int, tas: int) -> str:
  all_locations = [(random(), random()) for i in range(0, locations)]
  location_names = generate_names(locations)
  ta_locations = random_subset(list(range(0, locations)), tas)

  output = ""
  output += str(locations) + "\n"
  output += str(tas) + "\n"
  output += " ".join(location_names) + "\n"
  output += " ".join(map(lambda i: location_names[i], ta_locations)) + "\n"
  output += location_names[floor(random() * locations)] + "\n"

  matrix = [[ "x" for i in range(0, locations)] for j in range(0, locations)]
  for i in range(0, locations):
    for j in range(0, i):
      if random() < 0.25:
        i_loc = all_locations[i]
        j_loc = all_locations[j]
        delta_x = i_loc[0] - j_loc[0]
        delta_y = i_loc[1] - j_loc[1]
        dist = sqrt(delta_x * delta_x + delta_y * delta_y)
        matrix[i][j] = str(round(Decimal(dist), 5))
      matrix[j][i] = matrix[i][j]

  for i in range(0, locations):
    if i > 0:
      output += "\n"
    for j in range(0, locations):
      if j > 0:
        output += " "
      output += matrix[i][j]

  return output

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Parsing arguments')
  parser.add_argument('locations', type=int)
  parser.add_argument('tas', type=int)
  args = parser.parse_args()
  write_to_file(str(args.locations) + ".in", generate_input(args.locations, args.tas))
