import tkinter as tk
import sys
from enum import Enum
from random import randint


####### NOTES #######
# Bottlenecks and performance inefficiencies:
# - Mine placement is performed by picking random spots on the board
#   until one is not already a mine, then making it a mine. This works
#   to avoid the same spot being set to a mine more than once, but
#   introduces inefficiencies with higher mine:board size ratios.
#   Shouldn't result in infinite loop since checks are in place to ensure
#   TOTAL_MINES is not bigger than the board size when set. Upon testing,
#   even when the whole board is mines this does not seem to cause notable
#   performance issues, but is still worth noting as an inefficiency.
# - The biggest performance issue which causes very obvious delays is the
#   iterative destruction of every frame inside the board upon board regeneration.
#   This could maybe be avoided by deleting the board altogether and
#   adjusting the code for such an action accordingly? At worst this would
#   perform the same but at least lets tkinter handle destroying all the frames.
#   At best, tkinter has a much more optimized way of deleting them all this way.
#
# Bugs and general issues:
# - Larger boards and smaller screens lead to the program extending outside the
#   viewable area. There are two good solutions, best when combined based on
#   how much is out of view. The first is to simply decrease the size of the
#   frame pieces on the board. Once they start to become too small, it might
#   be necessary to incorporate some sort of scrolling, zooming, or panning feature.
#   This might be hard or impossible with tkinter (as I have it set up), except
#   with somewhat crude solutions. Do whatever works best, it doesn't have to be
#   pretty as long as it's fun and functional. The program should allow larger boards
#   and potentially ridiculous setups with the only limit being performance, not
#   UI challenges.
# - Recursion with RevealEmpty is not optimized, and maximum recursion depth can
#   be reached with bigger empty boards. Maybe change the recursion to a breadth-
#   first search.
#
# Possible additions and improvements:
# - Button or feature to view exposed board after loss (and mines after win).
#   Would have to work alongside baby mode, where the board shouldn't be
#   exposed if the player might opt to continue.
# - Change command-line argument parsing to something more dynamic and intuitive,
#   such as using parameters like '-y 80' and '-d' to set any paramter in any order.
# - Brainstorm and incorporate some novel mechanics or gameplay methods and
#   restrictions, either optional or fundamental. Minesweeper is just the
#   basic exercise, from which the game can expand into something unique.
#   Maybe even add different games and create a main menu to select among them.
# - Modify the board generation to occur on the first click, ensuring that the
#   clicked space is an empty spot, then process the reveal. This is a nice QoL
#   feature that I think most versions of Minesweeper have, and ensures the player
#   does not start the game by clicking on a mine or revealing a single useless space.
#


# Arguments passed to program
# Variables for controlling board size, number of mines, etc

n = len(sys.argv)

BOARD_WIDTH = int(sys.argv[1]) if (n > 1) else 20
BOARD_HEIGHT = int(sys.argv[2]) if (n > 2) else 20
TOTAL_MINES = int(sys.argv[3]) if (n > 3) else 60
# Validate mines is not larger than size of board
boardsize = BOARD_HEIGHT * BOARD_WIDTH
if TOTAL_MINES > boardsize:
    print(f"Defined number of mines ({TOTAL_MINES}) is larger than the size of the board ({BOARD_WIDTH} * {BOARD_HEIGHT} = {boardsize}). Setting mine count to {boardsize}")
    TOTAL_MINES = boardsize
PRINT_DEBUG_INFO = True if (n > 4 and sys.argv[4] == "True") else False

print(f"Opening Minesweeper game with board size {BOARD_WIDTH} x {BOARD_HEIGHT} with {TOTAL_MINES} "
      + "mines with%s debug info." %('' if PRINT_DEBUG_INFO else 'out'))


# Create the global window and variables
window = tk.Tk()
window.title("Minesweeper")
# Board is the gameplay area, menu is the UI below. Config is parametrization inside menu
board = tk.Frame(master=window)
menu = tk.Frame(master=window)
configframe = tk.Frame(master=menu)
# Inputs for changing the parameters of the board (upper limits can be increased)
widthpicker = tk.Spinbox(configframe, textvariable=tk.IntVar(window, BOARD_WIDTH), from_=1, to=100)
heightpicker = tk.Spinbox(configframe, textvariable=tk.IntVar(window, BOARD_HEIGHT), from_=1, to=100)
minepicker = tk.Spinbox(configframe, textvariable=tk.IntVar(window, TOTAL_MINES), from_=1, to=100)
# Variable for non-mine pieces left, displayed and used to determine when player has won.
pieces_left = (BOARD_HEIGHT * BOARD_WIDTH) - TOTAL_MINES
pieces_left_str = tk.StringVar(window, f"Pieces left: {pieces_left}")
# Bool for tracking if baby mode enabled
babymode = False

# Enumerator for representing a space's property
class Piece(Enum):
    HIDDEN = 0
    EMPTY = 1
    MINE = 2



# Functions

# Destroys the frames of the old board and returns a 2d array of hidden space values.
def ClearBoard():
    # Destroy every frame already in the board
    global board
    while len(board.grid_slaves()) > 0:
        if PRINT_DEBUG_INFO:
            print(f"Destroying board slave. {len(board.grid_slaves())} remaining.")
        board.grid_slaves()[0].destroy()
    # Return an empty 2d array of space values (not related to the board frames)
    return [ [{"type": Piece.HIDDEN, "count": 0, "flag": False} for j in range(BOARD_HEIGHT)] for i in range(BOARD_WIDTH)]

# Changes the color of the board. DOES NOT apply to newly created widgets, like labels in spaces.
def ChangeColor(color):
    for i in range(BOARD_HEIGHT):
        for j in range(BOARD_WIDTH):
            frame = board.grid_slaves(row=i, column=j)[0]
            if frame['bg'] != "red":
                frame.configure(bg=color)
                if len(frame.pack_slaves()) > 0:
                    frame.pack_slaves()[0].configure(bg=color)

# Sets baby mode (baby mode allows continuing on the same board after a loss)
def SetBabyMode():
    global babymode
    babymode = True
    ChangeColor("#8adaff")

# Updates board specs to user input and generates new board. Use when values should be updated.
def NewGame():
    global BOARD_WIDTH
    global BOARD_HEIGHT
    global TOTAL_MINES
    new_w = int(widthpicker.get())
    new_h = int(heightpicker.get())
    new_m = int(minepicker.get())
    # Validate mines can fit in board
    BOARD_WIDTH = new_w
    BOARD_HEIGHT = new_h
    if new_m <= new_w * new_h:
        TOTAL_MINES = new_m
    elif PRINT_DEBUG_INFO:
        print(f"Updated number of mines ({new_m}) is larger than the updated size of the board ({new_w} * {new_h} = {new_m * new_h}). Setting mine count to {new_m * new_h}")
        TOTAL_MINES = new_m * new_h
    if PRINT_DEBUG_INFO:
        print(f"Generating new board with size {BOARD_WIDTH} x {BOARD_HEIGHT} with {TOTAL_MINES}")
    GenerateBoard()

# Opens a popup window stating loss, allows Retry, Give Up, or Baby Mode
def GameOver(x,y):
    # Change clicked mine space to red
    board.grid_slaves(row=y, column=x)[0].configure(bg="red")
    # Create new window for game over prompt
    top= tk.Toplevel(window, padx=20, pady=20)
    top.title("Game Over")
    tk.Label(top, text= "You Lost!", font=('Mistral 18 bold')).pack()
    retry = tk.Button(top, text="Retry", command = lambda: [GenerateBoard(),top.destroy()])
    retry.pack(side=tk.LEFT)
    quit = tk.Button(top, text="Give Up", command = lambda: sys.exit())
    quit.pack(side=tk.LEFT)
    baby = tk.Button(top, text="Baby Mode", command = lambda: [SetBabyMode(), top.destroy()])
    baby.pack(side=tk.LEFT)
    # Set board regeneration on prompt window manual deletion
    top.protocol('WM_DELETE_WINDOW', lambda: [GenerateBoard(), top.destroy()])
    # Set game window unclickable while prompt is open
    top.transient(window)
    top.wait_visibility()
    top.grab_set()

# Similar to GameOver but for win prompt. Allows New Game or Quit
def GameWin():
    top= tk.Toplevel(window, padx=10, pady=20)
    top.title("You Win!")
    tk.Label(top, text= "Congratulations! You won!", font=('Mistral 18 bold')).pack()
    retry = tk.Button(top, text="New Game", command = lambda: [GenerateBoard(),top.destroy()])
    retry.pack()
    quit = tk.Button(top, text="Quit", command = lambda: sys.exit())
    quit.pack()
    top.transient(window)
    top.wait_visibility()
    top.grab_set()

# Reveals the space at the specified coordinate and, if empty, recursively reveals nearby spaces
# Note: this should not be used when a mine or flagged space is clicked.
def RevealEmpty(x,y):
    # Verify given coord is within board bounds
    if x >= 0 and x < BOARD_WIDTH and y >=0 and y < BOARD_HEIGHT:
        # Reference the frame and associated piece represenation at the coords
        wframe = board.grid_slaves(row=y, column=x)[0]
        piece = spaces[x][y]
        # Verify piece is not mine, and is still hidden
        if piece["type"] == Piece.HIDDEN:
            # Remove flag on piece being revealed (only happens to spaces recursively revealed)
            if piece["flag"]:
                piece["flag"] = False
                wframe.pack_slaves()[0].destroy()
            # Change piece to empty and update frame appearance
            piece["type"] = Piece.EMPTY
            wframe.configure(relief=tk.FLAT)
            # If piece's count is 0, create a label with according number and color
            if piece["count"] > 0:
                wframe.configure(relief=tk.RAISED, borderwidth=1)
                if piece["count"] == 1:
                    color = "blue"
                elif piece["count"] == 2:
                    color = "green"
                elif piece["count"] == 2:
                    color = "yellow"
                elif piece["count"] == 3:
                    color = "red"
                elif piece["count"] == 4:
                    color = "#571100"
                elif piece["count"] == 5:
                    color = "magenta"
                else:
                    color = "black"
                label = tk.Label(master=wframe, text=str(piece["count"]), fg=color)
                if babymode:
                    label.configure(bg='#8adaff')
                label.bind("<Button-1>", ClickSpace)
                label.bind("<Button-3>", RightClickSpace)
                label.pack()
            # If piece has no adjacent mine count, recursively reveal all 8 surrounding spaces
            else:
                RevealEmpty(x-1,y-1)
                RevealEmpty(x-1,y)
                RevealEmpty(x-1,y+1)
                RevealEmpty(x,y-1)
                RevealEmpty(x,y+1)
                RevealEmpty(x+1,y-1)
                RevealEmpty(x+1,y)
                RevealEmpty(x+1,y+1)
            # Decrement number of remaining non-mine pieces
            global pieces_left
            pieces_left -= 1
            pieces_left_str.set(f"Pieces left: {pieces_left}")
            if PRINT_DEBUG_INFO:
                print(f"Revealing pieces at x:{x} y:{y}")
                print(f"Pieces left: {pieces_left}")
            # Win condition: if all non-mine pieces are revealed, the game is won.
            if pieces_left <= 0:
                GameWin()

# Event for left-clicking on any frame in the board. Will handle accordingly.
def ClickSpace(event):
    wframe = event.widget
    # If label is clicked, change wframe reference to its master frame
    if isinstance(wframe, tk.Label):
        wframe = wframe.master
    # Get grid coords of frame clicked and associated piece
    grid_info = wframe.grid_info()
    x = grid_info['column']
    y = grid_info['row']
    piece = spaces[x][y]
    if PRINT_DEBUG_INFO:
        print(f"Piece: {piece['type']} clicked at space: {x}, {y}")
    # If flag is LEFT-clicked, do nothing.
    if piece["flag"]:
        if PRINT_DEBUG_INFO:
            print("Clicked Piece is a flag")
    # If mine is clicked, game over!
    elif piece["type"] == Piece.MINE:
        GameOver(x,y)
    # If hidden piece clicked, reveal it.
    elif piece["type"] == Piece.HIDDEN:
        RevealEmpty(x,y)
    # Else piece must be already revealed, so do nothing.
    elif PRINT_DEBUG_INFO:
        print("Clicked piece is empty")

# Event for right-clicking any frame on the board. Used for flagging pieces.
def RightClickSpace(event):
    wframe = event.widget
    # If label is clicked, change wframe reference to its master frame
    if isinstance(wframe, tk.Label):
        wframe = wframe.master
    # Get grid coords of frame clicked and associated piece
    grid_info = wframe.grid_info()
    x = grid_info['column']
    y = grid_info['row']
    piece = spaces[x][y]
    if PRINT_DEBUG_INFO:
        print(f"Piece: {piece['type']} right clicked at space: {x}, {y}")
    # If piece is already revealed, do nothing.
    if piece["type"] == Piece.MINE or piece["type"] == Piece.HIDDEN:
        # Toggle flag status of piece and update frame accordingly
        if piece["flag"]:
            piece["flag"] = False
            wframe.pack_slaves()[0].destroy()
        else:
            piece["flag"] = True
            label = tk.Label(master=wframe, text='!!', fg="red")
            # New flags must be given background color here if necessary
            if babymode:
                label.configure(bg='#8adaff')
            label.bind("<Button-1>", ClickSpace)
            label.bind("<Button-3>", RightClickSpace)
            label.pack()
    else:
        if PRINT_DEBUG_INFO:
            print("Clicked piece is not mine or hidden")

# Increments the adjacent mine count of the piece at the given coords. Used when placing mines.
def AddCount(x,y):
    if x >= 0 and x < BOARD_WIDTH and y >=0 and y < BOARD_HEIGHT:
        spaces[x][y]["count"] += 1

# The function for initial and subsequent generation of a new game.
# Resets necessary variables, initializes board with ClearBoard(), places mines, and creates frames.
def GenerateBoard():
    # Reset variables to initial values
    global spaces
    global board
    global pieces_left
    global babymode
    spaces = ClearBoard()
    pieces_left = (BOARD_HEIGHT * BOARD_WIDTH) - TOTAL_MINES
    pieces_left_str.set(f"Pieces left: {pieces_left}")
    babymode = False

    # Randomly place mines one at a time
    for i in range(TOTAL_MINES):
        y = randint(0,BOARD_HEIGHT-1)
        x = randint(0, BOARD_WIDTH-1)
        # Pick another random spot until the space is not a mine
        while spaces[x][y]["type"] == Piece.MINE:
            y = randint(0,BOARD_HEIGHT-1)
            x = randint(0, BOARD_WIDTH-1)
        # Set the space to a mine
        spaces[x][y]["type"] = Piece.MINE
        if PRINT_DEBUG_INFO:
            print(f"Placing mine at space x:{x} y:{y}")
        # Add 1 to each surrounding space
        AddCount(x-1,y-1)
        AddCount(x-1,y)
        AddCount(x-1,y+1)
        AddCount(x,y-1)
        AddCount(x,y+1)
        AddCount(x+1,y-1)
        AddCount(x+1,y)
        AddCount(x+1,y+1)

    # Add a frame for each space on the board
    for i in range(BOARD_HEIGHT):
        for j in range(BOARD_WIDTH):

            frame = tk.Frame(
                master=board,
                relief=tk.RAISED,
                borderwidth=5,
                width=30,
                height=30,
                )
            frame.pack_propagate(False)
            frame.bind("<Button-1>", ClickSpace)
            frame.bind("<Button-3>", RightClickSpace)
            frame.grid(row=i, column=j)
    board.pack()


# Initialize spaces and generate board
spaces = ClearBoard()
GenerateBoard()
# Assemble menu GUI
widthpicker.pack()
heightpicker.pack()
minepicker.pack()
configframe.pack(side=tk.LEFT)
replayBtn = tk.Button(menu, padx=10, text="Regenerate", command=NewGame)
replayBtn.pack(side=tk.LEFT)
minelabel = tk.Label(menu, padx=20, textvariable=pieces_left_str).pack(side=tk.LEFT)
menu.pack(padx=10,pady=10)

# Run program
window.mainloop()
