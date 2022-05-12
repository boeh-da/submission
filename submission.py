# Imports helper functions
from kaggle_environments.envs.halite.helpers import *
import random
import math

BOTNAME = 'Uni-Tasker'

# Returns best direction to move from one position (fromPos) to another (toPos)
def getDirTo(fromPos, toPos, size):
    fromX, fromY = divmod(fromPos[0],size), divmod(fromPos[1],size)
    toX, toY = divmod(toPos[0],size), divmod(toPos[1],size)
    if fromY < toY: return ShipAction.NORTH
    if fromY > toY: return ShipAction.SOUTH
    if fromX < toX: return ShipAction.EAST
    if fromX > toX: return ShipAction.WEST

# Find objects of other players
def objectsOfOthers(board):
    # list of (x, y) coords
    other_ships = []
    other_shipyards = []
    
    for player in board.opponents:
        for ship in player.ships:
            pos = ship.position
            halite_ship = ship.halite
            other_ships.append((pos, halite_ship))
        for shipyard in player.shipyards:
            pos = shipyard.position
            num_ships = len(player.ships)
            other_shipyards.append((pos, num_ships))
                
    return other_ships, other_shipyards

# Find nearest objects to ships
def nearestObject(fromPos, positions, size):
    fromX, fromY = fromPos
    distance = []
    for obj, halite in positions:
        toX, toY = obj
        distance.append(math.sqrt((toX-fromX)**2 + (toY-fromY)**2))
    nearest = min(distance)
    index = distance.index(nearest)
    return positions[index]

# Code to attack closest ship
def attackShip(ship, other_ships, size, other_shipyards, step):
    try:
        attack = nearestObject(ship.position, other_ships, size)
        pos, halite = attack
    except:
        halite = 0

    if halite > 10 and halite > ship.halite:
        other_ships = other_ships.remove(attack)
        return getDirTo(ship.position, pos, size)
    else:
        if step > 300: 
            return attackShipyard(ship,other_shipyards, size )
        else: 
            return random.choice([ShipAction.NORTH, None, ShipAction.EAST])

def newPosition (old_position, next_step):
    x, y = old_position
    if next_step == ShipAction.NORTH: return (x, y+1)
    if next_step == ShipAction.SOUTH: return (x, y-1)
    if next_step == ShipAction.EAST: return (x+1, y)
    if next_step == ShipAction.WEST: return (x-1, y)
    if next_step == None: return (x, y)


# Code to attack shipyard: write if's in agent
def attackShipyard(ship, other_shipyards, size):
    attack = nearestObject(ship.position, other_shipyards, size)
    pos, halite = attack
    return getDirTo(ship.position, pos, size)
    

# Directions a ship can move
directions = [ShipAction.NORTH, ShipAction.EAST, ShipAction.SOUTH, ShipAction.WEST]

# Will keep track of whether a ship is collecting halite or carrying cargo to a shipyard
ship_states = {}

def enemy_near(ship, positions):
    sx, sy = ship.position
    for pos, halite in positions:
        if (sx-1<=pos[0]<=sx+1) and (sy-1<=pos[1]<=sy+1):
            if halite < ship.halite:
                return True
    else:
        False

def runaway(ship, position):
    sx, sy = ship.position
    for pos, halite in position:
        if pos[0] == sx+1:
            return ShipAction.SOUTH
        elif pos[0] == sx-1:
            return ShipAction.NORTH
        elif pos[1] == sy-1:
            return ShipAction.EAST
        elif pos[1] == sy+1:
            return ShipAction.WEST

def flip(action):
    dirs  = [ShipAction.NORTH, ShipAction.EAST, ShipAction.SOUTH, ShipAction.WEST]
    try: 
        dirs.remove(action)
    except:
        pass
    return random.choice(dirs)


# Returns the commands we send to our ships and shipyards
def agent(obs, config):
    size = config.size
    board = Board(obs, config)
    me = board.current_player

    # If there are no ships, use first shipyard to spawn a ship.
    if len(me.ships) == 0 and len(me.shipyards) > 0:
        me.shipyards[0].next_action = ShipyardAction.SPAWN

    # If there are no shipyards, convert first ship into shipyard.
    if len(me.shipyards) == 0 and len(me.ships) > 0:
        me.ships[0].next_action = ShipAction.CONVERT
        
        
    other_ships, other_shipyards = objectsOfOthers(board)
    ship_positions = []
        
    # Actions for each ships
    for ship in me.ships:
        if ship.next_action == None:
            
            if enemy_near(ship, other_ships): 
                ship_states[ship.id] = "RUNAWAY"
            elif ship.halite > 1:
                ship_states[ship.id] = "DEPOSIT"
            else: 
                ship_states[ship.id] = "ATTACK"

                
            ### Part 2: Use the ship's state to select an action
            if ship_states[ship.id] == "RUNAWAY":
                direction = runaway(ship, other_ships)
                if direction: ship.next_action = direction
            if ship_states[ship.id] == "ATTACK":
                direction = attackShip(ship, other_ships, size, other_shipyards, board.step)
                if direction: ship.next_action = direction
            if ship_states[ship.id] == "CONVERT":
                # Move towards shipyard to deposit cargo
                ship.next_action = ShipAction.CONVERT
            if ship_states[ship.id] == "DEPOSIT":
                # Move towards shipyard to deposit cargo
                direction = getDirTo(ship.position, me.shipyards[0].position, size)
                if direction: ship.next_action = direction
             
            new_position = newPosition(ship.position, ship.next_action)
            # Avoid Shipyards
            if new_position in [x[0] for x in other_shipyards]:
                ship.next_action = flip(ship.next_action)
                new_position = newPosition(ship.position, ship.next_action)
            # Avoid Collisions
            for other_position in ship_positions:
                if new_position == other_position:
                    ship.next_action = flip(ship.next_action)
                    new_position = newPosition(ship.position, ship.next_action)
            ship_positions.append(new_position)

    # Collision Detection 2nd Level
    ship_positions = []
    for ship in me.ships:
        new_position = newPosition(ship.position, ship.next_action)
        for other_position in ship_positions:
            if new_position == other_position:
                ship.next_action = flip(ship.next_action)
                new_position = newPosition(ship.position, ship.next_action)
        ship_positions.append(new_position)
    
    for shipyards in me.shipyards:
        spawnShip = True
        for position in ship_positions:
            if position == shipyards.position:
                spawnShip = False
        if shipyards.next_action == None and spawnShip == True:
            if me.halite > 500 and len(me.ships) <= 10 and board.step < 300:
                shipyards.next_action = ShipyardAction.SPAWN
                
                
    return me.next_actions


