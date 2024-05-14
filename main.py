from game_logic.game import GameLoop


if "__main__" == __name__:
    rows = 10
    columns = 10
    cell_size = 20

    game_loop = GameLoop(rows, columns, cell_size)
    game_loop.run()