#!/usr/bin/env python3

import os
import sys
sys.path.append('..')
sys.path.append('../..')
import argparse
import utils
import networkx as nx
from mip import Model, xsum, minimize, BINARY, INTEGER, GUROBI
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

    tas = range(0, len(list_of_homes))
    nTas = len(tas)
    home_indices = list(map(lambda home: location_name_to_index[home], list_of_homes))

    starting_car_index = location_name_to_index[starting_car_location]

    (G, message) = adjacency_matrix_to_graph(adjacency_matrix)
    shortest_paths = nx.floyd_warshall(G)
    L = range(0, len(list_of_locations))
    nL = len(L)

    model = Model()
    model.threads = 8

    edge_taken = [[model.add_var(var_type=BINARY) for j in L] for i in L]
    visited_step = [model.add_var() for i in L]
    drop_ta_at_stop = [[model.add_var(var_type=BINARY) for stop in L] for ta in tas]

    driving_cost = (2 / 3) * xsum(
        G.edges[i, j]["weight"] * edge_taken[i][j]
        for i in L for j in L if G.has_edge(i, j)
    )

    walking_cost = xsum(
        shortest_paths[home_indices[ta]][stop] * drop_ta_at_stop[ta][stop]
        for stop in L for ta in tas
    )

    model.objective = minimize(driving_cost + walking_cost)

    # only take edges that exist
    for i in L:
        for j in L:
            if not G.has_edge(i, j):
                model += edge_taken[i][j] == 0

    # enter city same number of times as we exist the city
    for i in L:
        model += xsum(edge_taken[incoming][i] for incoming in L) == xsum(edge_taken[i][to] for to in L)

    if False: # MCF formulation
        ta_over_edge = [[[model.add_var(var_type=BINARY) for ta in tas] for j in L] for i in L]
        
        # each TA gets dropped off at their stop
        for node in (set(L) - {starting_car_index}):
            for ta in tas:
                ta_entering_node = xsum(
                    ta_over_edge[prev][node][ta]
                    for prev in L
                )

                ta_leaving_node = xsum(
                    ta_over_edge[node][nxt][ta]
                    for nxt in L
                )

                ta_dropped_at_stop = drop_ta_at_stop[ta][node]

                model += ta_entering_node == ta_leaving_node + ta_dropped_at_stop

        # each TA must be dropped off somewhere along the route
        for ta in tas:
            leaving_start = xsum(ta_over_edge[starting_car_index][nxt][ta] for nxt in L)
            returning_start = xsum(ta_over_edge[prev][starting_car_index][ta] for prev in L)
            model += leaving_start == 1 - drop_ta_at_stop[ta][starting_car_index] # drop TA off right before we leave
            model += returning_start == 0

        # if a TA goes over an edge, we must take it as well
        for i in L:
            for j in L:
                for ta in tas:
                    model += edge_taken[i][j] >= ta_over_edge[i][j][ta]
    else: # SCF formulation
        flow_over_edge = [[model.add_var(var_type=INTEGER) for j in L] for i in L]

        # flow decreases only when TAs are dropped off
        for node in (set(L) - {starting_car_index}):
            tas_entering_node = xsum(
                flow_over_edge[prev][node]
                for prev in L
            )

            tas_leaving_node = xsum(
                flow_over_edge[node][nxt]
                for nxt in L
            )

            tas_dropped_at_stop = xsum(drop_ta_at_stop[ta][node] for ta in tas)

            model += tas_entering_node == tas_leaving_node + tas_dropped_at_stop

        # each TA must be dropped off somewhere along the route
        leaving_start = xsum(flow_over_edge[starting_car_index][nxt] for nxt in L)
        returning_start = xsum(flow_over_edge[prev][starting_car_index] for prev in L)
        model += leaving_start == nTas - xsum(drop_ta_at_stop[ta][starting_car_index] for ta in tas)
        model += returning_start == 0

        # if flow goes over an edge, we must take it as well
        for i in L:
            for j in L:
                model += edge_taken[i][j] * nTas >= flow_over_edge[i][j]

    # every TA is dropped off at exactly one stop
    for ta in tas:
        model += xsum(drop_ta_at_stop[ta][stop] for stop in L) == 1

    print(model.constrs)
    status = model.optimize()
    if model.num_solutions:
        edge_graph = nx.DiGraph()
        print("Edges taken:")
        count = 0
        for i in range(0, nL):
            for j in range(0, nL):
                if (edge_taken[i][j].x >= 0.99):
                    edge_graph.add_edge(i, j)
                    print(i, j, G.edges[i, j]["weight"])
                    count += 1
        
        print("Path:")
        path = [u for u, v in nx.eulerian_circuit(edge_graph, source=starting_car_index)] + [starting_car_index]
        for node in path:
            print(node)

        dropoffs = {}
        for ta in tas:
            drop_off_stop = [i for i in L if drop_ta_at_stop[ta][i].x >= 0.99][0]
            if not drop_off_stop in dropoffs:
                dropoffs[drop_off_stop] = []
            dropoffs[drop_off_stop].append(home_indices[ta])
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
