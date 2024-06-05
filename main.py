from game_instances.local_loop import LocalLoop


if "__main__" == __name__:
    rows = 10
    columns = 10
    cell_size = 20

    game_loop = LocalLoop(rows, columns, cell_size)
    game_loop.run()
