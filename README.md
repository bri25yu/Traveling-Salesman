# project-fa19
CS 170 Fall 2019 Project

## Installation
This solver requires a few additional dependencies on top of the built-in ones.

Run `pip3 install networkx mip numpy` to install the extra dependencies.

The solver works with both the CBC open-source solver as well as the Gurobi solver (which we used with an academic license). The `mip` library will automatically pick up the best solver based on what is installed.

## Solving Inputs
Our solver uses the same CLI format as the template project. To run the solver on all inputs, run `python3 solver.py --all inputs outputs`. To solve on a specific input, run `python3 solver.py INSERT-INPUT-HERE outputs`
