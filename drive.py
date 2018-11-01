#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess

init_grid = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0, 0],
    [1, 1, 0, 0, 0, 1, 1, 0, 0],
    [1, 1, 0, 0, 0, 0, 0, 0, 0]
]

def to_binary(data):
    field = [['0'] * 27, ['0'] * 27, ['0'] * 27]
    for i in range(3):
        for y in range(i * 3, i * 3 + 3):
            for x in range(0, 9):
                if data[y][x]:
                    field[i][26 - (y % 3 * 9 + x)] = '1'
    return [int("".join(line), 2) for line in field]

def start_proc(command):
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def write_to_proc(proc, payload):
    proc.stdin.write(payload.encode('utf-8'))
    proc.stdin.flush()

def read_from_proc(proc):
    return proc.stdout.readline().decode('utf-8').strip()

if __name__ == '__main__':
    init_data = to_binary(init_grid)

    player_blue = start_proc(['python', 'main.py'])
    player_red = start_proc(['python', 'main.py'])

    write_to_proc(player_blue, json.dumps({'field': init_data, 'mySide': 0}) + '\n')
    write_to_proc(player_red, json.dumps({'field': init_data, 'mySide': 1}) + '\n')

    while True:
        r1 = read_from_proc(player_blue)
        r2 = read_from_proc(player_red)

        print('r1', r1)
        print('r2', r2)
        print('-----------------------------')

        res1 = {
            'requests': [json.loads(r2)['response']],
            'responses': [],
        }

        res2 = {
            'requests': [json.loads(r1)['response']],
            'responses': [],
        }

        write_to_proc(player_blue, json.dumps(res1) + '\n')
        write_to_proc(player_red, json.dumps(res2) + '\n')
