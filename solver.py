#!/usr/bin/env python3

import os
import sys
sys.path.append('..')
sys.path.append('../..')
import argparse
import utils
import networkx as nx
from mip import Model, xsum, minimize, BINARY, INTEGER
from itertools import product

from student_utils import *
"""
======================================================================
  Complete the following function.
======================================================================
"""

def solve(list_of_locations, list_of_homes, starting_car_location, adjacency_matrix, params=[]):
    """
    Write your algorithm here.
    Input:
        list_of_locations: A list of locations such that node i of the graph corresponds to name at index i of the list
        list_of_homes: A list of homes
        starting_car_location: The name of the starting location for the car
        adjacency_matrix: The adjacency matrix from the input file
    Output:
        A list of locations representing the car path
        A dictionary mapping drop-off location to a list of homes of TAs that got off at that particular location
        NOTE: both outputs should be in terms of indices not the names of the locations themselves
    """

    location_name_to_index = {}
    for i in range(0, len(list_of_locations)):
        location_name_to_index[list_of_locations[i]] = i

    home_indices = list(map(lambda home: location_name_to_index[home], list_of_homes))

    starting_car_index = location_name_to_index[starting_car_location]

    (G, message) = adjacency_matrix_to_graph(adjacency_matrix)
    shortest_paths = nx.floyd_warshall(G)
    L = range(0, len(list_of_locations))
    nL = len(L)

    model = Model()
    edges_taken = [[model.add_var(var_type=BINARY) for j in L] for i in L]
    visited_step = [model.add_var() for i in L]

    model.objective = minimize(xsum(
        G.edges[i, j]["weight"] * edges_taken[i][j] for i in L for j in L if G.has_edge(i, j)
    ))

    for i in L:
        for j in L:
            if not G.has_edge(i, j):
                model += edges_taken[i][j] == 0

    for city in [starting_car_index] + home_indices:
        # enter city once
        model += xsum(edges_taken[i][city] for i in set(L) - {city}) == 1
        # leave city once
        model += xsum(edges_taken[city][j] for j in set(L) - {city}) == 1

    # enter and exit city once (this can be removed I think, but need to adjust path following logic)
    for i in L:
        model += xsum(edges_taken[incoming][i] for incoming in set(L) - {i}) <= 1
        model += xsum(edges_taken[i][to] for to in set(L) - {i}) <= 1

    # enter city same number of times as we exist the city
    for i in L:
        model += xsum(edges_taken[incoming][i] for incoming in set(L) - {i}) - xsum(edges_taken[i][to] for to in set(L) - {i}) == 0

    # no subtours (Miller-Tucker-Zemlin formulation)
    for (i, j) in set(product(set(L) - {0}, set(L) - {0})):
        if i != j:
            model += visited_step[i] - (nL + 1) * edges_taken[i][j] >= visited_step[j] - nL

    for i in range(1, nL):
        model += visited_step[i] >= 0
        model += visited_step[i] <= nL - 1

    status = model.optimize(max_seconds=300)
    if model.num_solutions:
        print("Edges taken:")
        count = 0
        for i in range(0, nL):
            for j in range(0, nL):
                if (edges_taken[i][j].x >= 0.99):
                    print(i, j, G.edges[i, j]["weight"])
                    count += 1
        
        print("Path:")
        next_city = starting_car_index
        other_count = 0
        path = []
        dropoffs = {}

        while True:
            print(next_city)
            path.append(next_city)
            next_city = [i for i in L if edges_taken[next_city][i].x >= 0.99][0]
            other_count += 1
            if next_city == starting_car_index:
                print(next_city)
                path.append(next_city)
                break

        for home in list_of_homes:
            dropoffs[location_name_to_index[home]] = [location_name_to_index[home]]

        # verify that we actually used all the edges we took, because I'm not 100% confident
        # that the formulation works when we only need to visit a subset of nodes
        if count != other_count:
            print(count)
            print(other_count)
            raise RuntimeError("SOMETHING WRONG")
        return (path, dropoffs)

    return ([], {})


"""
======================================================================
   No need to change any code below this line
======================================================================
"""

"""
Convert solution with path and dropoff_mapping in terms of indices
and write solution output in terms of names to path_to_file + file_number + '.out'
"""
def convertToFile(path, dropoff_mapping, path_to_file, list_locs):
    string = ''
    for node in path:
        string += list_locs[node] + ' '
    string = string.strip()
    string += '\n'

    dropoffNumber = len(dropoff_mapping.keys())
    string += str(dropoffNumber) + '\n'
    for dropoff in dropoff_mapping.keys():
        strDrop = list_locs[dropoff] + ' '
        for node in dropoff_mapping[dropoff]:
            strDrop += list_locs[node] + ' '
        strDrop = strDrop.strip()
        strDrop += '\n'
        string += strDrop
    utils.write_to_file(path_to_file, string)

def solve_from_file(input_file, output_directory, params=[]):
    print('Processing', input_file)

    input_data = utils.read_file(input_file)
    num_of_locations, num_houses, list_locations, list_houses, starting_car_location, adjacency_matrix = data_parser(input_data)
    car_path, drop_offs = solve(list_locations, list_houses, starting_car_location, adjacency_matrix, params=params)

    basename, filename = os.path.split(input_file)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    output_file = utils.input_to_output(input_file, output_directory)

    convertToFile(car_path, drop_offs, output_file, list_locations)


def solve_all(input_directory, output_directory, params=[]):
    input_files = utils.get_files_with_extension(input_directory, 'in')

    for input_file in input_files:
        solve_from_file(input_file, output_directory, params=params)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Parsing arguments')
    parser.add_argument('--all', action='store_true', help='If specified, the solver is run on all files in the input directory. Else, it is run on just the given input file')
    parser.add_argument('input', type=str, help='The path to the input file or directory')
    parser.add_argument('output_directory', type=str, nargs='?', default='.', help='The path to the directory where the output should be written')
    parser.add_argument('params', nargs=argparse.REMAINDER, help='Extra arguments passed in')
    args = parser.parse_args()
    output_directory = args.output_directory
    if args.all:
        input_directory = args.input
        solve_all(input_directory, output_directory, params=args.params)
    else:
        input_file = args.input
        solve_from_file(input_file, output_directory, params=args.params)
