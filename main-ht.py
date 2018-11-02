# Tank 游戏样例程序
# 随机策略
# 作者：zhouhy
# https://www.botzone.org.cn/games/Tank
import json
import sys
import random
from typing import List

FIELD_HEIGHT = 9
FIELD_WIDTH = 9
SIDE_COUNT = 2
TANK_PER_SIDE = 2

dx = [ 0, 1, 0, -1 ]
dy = [ -1, 0, 1, 0 ]

class FieldItemType():
    Nil = 0
    Brick = 1
    Steel = 2
    Base = 3
    Tank = 4

class Action():
    Invalid = -2
    Stay = -1
    Up = 0
    Right = 1
    Down = 2
    Left = 3
    UpShoot = 4
    RightShoot = 5
    DownShoot = 6
    LeftShoot = 7

class WhoWins():
    NotFinished = -2
    Draw = -1
    Blue = 0
    Red = 1

class FieldObject:
    def __init__(self, x: int, y: int, itemType: FieldItemType):
        self.x = x
        self.y = y
        self.itemType = itemType
        self.destroyed = False

class Base(FieldObject):
    def __init__(self, side: int):
        super().__init__(4, side * 8, FieldItemType.Base)
        self.side = side

class Tank(FieldObject):
    def __init__(self, side: int, tankID: int, x: int = -1, y: int = -1):
        super().__init__(x if x != -1 else (6 if side ^ tankID else 2), y if y != -1 else (side * 8), FieldItemType.Tank)
        self.side = side
        self.tankID = tankID

class TankField:

    def __init__(self):
        self.fieldContent = [
            [[] for x in range(FIELD_WIDTH)] for y in range(FIELD_HEIGHT)
        ]
        self.tanks = [[Tank(s, t) for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.bases = [Base(s) for s in range(SIDE_COUNT)]
        self.lastActions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.actions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.currentTurn = 1

        for tanks in self.tanks:
            for tank in tanks:
                self.insertFieldItem(tank)
        for base in self.bases:
            self.insertFieldItem(base)
        self.insertFieldItem(FieldObject(4, 1, FieldItemType.Steel))
        self.insertFieldItem(FieldObject(4, 7, FieldItemType.Steel))

    def insertFieldItem(self, item: FieldObject):
        self.fieldContent[item.y][item.x].append(item)
        item.destroyed = False

    def removeFieldItem(self, item: FieldObject):
        self.fieldContent[item.y][item.x].remove(item)
        item.destroyed = True

    def fromBinary(self, bricks: List[int]):
        for i in range(3):
            mask = 1
            for y in range(i * 3, i * 3 + 3):
                for x in range(FIELD_WIDTH):
                    if bricks[i] & mask:
                        self.insertFieldItem(FieldObject(x, y, FieldItemType.Brick))
                    mask = mask << 1

    def fromMatrix(self, m):
        for y in range(0, FIELD_HEIGHT):
            for x in range(0, FIELD_WIDTH):
                if m[y][x] == 0:
                    self.fieldContent[y][x] = []
                elif m[y][x] == 1:
                    self.fieldContent[y][x] = [FieldObject(x, y, FieldItemType.Brick)]
                elif m[y][x] in [-1, -2, -3, -4]:
                    side, no = (-m[y][x] - 1) // 2, (-m[y][x] - 1) % 2
                    self.tanks[side][no] = Tank(side, no, x, y)
                    self.fieldContent[y][x] = [self.tanks[side][no]]
                else:
                    pass

    def actionValid(self, side: int, tank: int, action: Action) -> bool:
        if action >= Action.UpShoot and self.lastActions[side][tank] >= Action.UpShoot:
            return False
        if action == Action.Stay or action >= Action.UpShoot:
            return True
        x = self.tanks[side][tank].x + dx[action]
        y = self.tanks[side][tank].y + dy[action]
        return self.inRange(x, y) and not self.fieldContent[y][x]

    def noBrick(self, x1, y1, x2, y2):
        if x1 != x2 and y1 != y2:
            return False
        if x1 == x2 and y1 == y2:
            return False
        if x1 == x2:
            y1, y2 = min(y1, y2), max(y1, y2)
            for yi in range(y1 + 1, y2):
                if self.fieldContent[yi][x1] and not self.fieldContent[yi][x1][0].destroyed:
                    return False
            return True
        else:
            x1, x2 = min(x1, x2), max(x1, x2)
            for xi in range(x1 + 1, x2):
                if self.fieldContent[y1][xi] and not self.fieldContent[y1][xi][0].destroyed:
                    return False
            return True

    def canShootBase(self, side: int, tank: int):
        x, y = self.tanks[side][tank].x, self.tanks[side][tank].y
        tx, ty = self.bases[1-side].x, self.bases[1-side].y
        if y == ty:
            if self.noBrick(x, y, tx, ty):
                return Action.LeftShoot if x > tx else Action.RightShoot
            for target in range(TANK_PER_SIDE):
                if self.canShootTank(side, tank, target) != Action.Invalid:
                    return Action.Invalid
            return Action.LeftShoot if x > tx else Action.RightShoot
        else:
            return Action.Invalid

    def canShootTank(self, side: int, tank: int, target: int, movex: int = 0, movey: int = 0):
        x, y = self.tanks[side][tank].x + movex, self.tanks[side][tank].y + movey
        tx, ty = self.tanks[1 - side][target].x, self.tanks[1 - side][target].y

        if (x == tx and y == ty): return Action.Invalid
        if self.tanks[1 - side][target].destroyed:
            return Action.Invalid
        if self.noBrick(x, y, tx, ty):
            if x == tx:
                return Action.UpShoot if y > ty else Action.DownShoot
            else:
                return Action.LeftShoot if x > tx else Action.RightShoot
        else:
            return Action.Invalid

    # when the target move upwards, if we can hit it
    def canShootTankUpwards(self, side: int, tank: int, target: int, steps: int = 1):
        x, y = self.tanks[side][tank].x, self.tanks[side][tank].y
        tx, ty = self.tanks[1 - side][target].x, self.tanks[1 - side][target].y - steps
        if ty < 0:
            return Action.Invalid
        if self.noBrick(x, y, tx, ty):
            if x == tx:
                return Action.Invalid
                # return Action.UpShoot if y > ty else Action.DownShoot
            else:
                if self.canMove(1-side, target, Action.Up):
                    return Action.LeftShoot if x > tx else Action.RightShoot
                else:
                    return Action.Invalid
        else:
            return Action.Invalid

    # when the target move downwards, if we can hit it
    def canShootTankDownwords(self, side: int, tank: int, target: int, steps: int = 1):
        x, y = self.tanks[side][tank].x, self.tanks[side][tank].y
        tx, ty = self.tanks[1 - side][target].x, self.tanks[1 - side][target].y + steps
        if ty >= FIELD_HEIGHT:
            return Action.Invalid
        if self.noBrick(x, y, tx, ty):
            if x == tx:
                return Action.Invalid
                # return Action.UpShoot if y > ty else Action.DownShoot
            else:
                if self.canMove(1-side, target, Action.Down):
                    return Action.LeftShoot if x > tx else Action.RightShoot
                else:
                    return Action.Invalid
        else:
            return Action.Invalid

    def canMove(self, side: int, tank: int, move: int):
        x, y = self.tanks[side][tank].x, self.tanks[side][tank].y
        tx, ty = x, y
        if move == Action.Left:
            tx = tx - 1
        elif move == Action.Right:
            tx = tx + 1
        elif move == Action.Up:
            ty = ty - 1
        else:
            ty = ty + 1
        if tx < 0 or tx >= FIELD_WIDTH or ty < 0 or ty >= FIELD_HEIGHT:
            return False
        if tx == self.tanks[side][1-tank].x and ty == self.tanks[side][1-tank].y:
            return True
        if self.fieldContent[ty][tx] and \
                self.fieldContent[ty][tx][0].itemType == FieldItemType.Tank:
            return True
        if self.fieldContent[ty][tx] and not self.fieldContent[ty][tx][0].destroyed:
            return False
        return True

    def canShot(self, side: int, tank: int, shoot: int):
        x, y = self.tanks[side][tank].x, self.tanks[side][tank].y
        dx, ty = 0, 0
        if shoot == Action.LeftShoot:
            dx = - 1
        elif shoot == Action.RightShoot:
            dx = 1
        elif shoot == Action.UpShoot:
            dy = - 1
        else:
            dy = 1
        x, y = x + dx, y + dy
        while x >= 0 and x < FIELD_WIDTH and y >= 0 and y < FIELD_HEIGHT:
            if x == self.tanks[side][1-tank].x and y == self.tanks[side][1-tank].y:
                return False # don't suicide
            if self.fieldContent[y][x] and self.fieldContent[y][x][0].itemType == FieldItemType.Steel:
                return False
            if self.fieldContent[y][x] and self.fieldContent[y][x][0].itemType == FieldItemType.Brick:
                return True
            if self.fieldContent[y][x] and self.fieldContent[y][x][0].itemType == FieldItemType.Base:
                return True
            if self.fieldContent[y][x] and self.fieldContent[y][x][0].itemType == FieldItemType.Tank:
                return True
        return False

    def enemyBaseOnSameRow(self, side: int, tank: int) -> bool:
        pos_y = self.tanks[side][tank].y

        base_y = self.bases[1 - side].y

        return (pos_y == base_y)

    def enemyTankOnSameRow(self, side: int, tank: int) -> bool:
        pos_y = self.tanks[side][tank].y
        pos_x = self.tanks[side][tank].x

        for k in self.tanks[1 - side]:
            # Two tanks on the same side
            if (k.x - FIELD_WIDTH // 2) * (pos_x - FIELD_WIDTH // 2) > 0:
                if pos_y == k.y: return True
        return False

    def leftToBase(self, side: int, tank: int) -> bool:
        pos_x = self.tanks[side][tank].x

        base_x = self.bases[1 - side].x

        return (pos_x < base_x)

    def leftToTank(self, side: int, tank: int) -> bool:
        pos_y = self.tanks[side][tank].y
        pos_x = self.tanks[side][tank].x

        for k in self.tanks[1 - side]:
            # Two tanks on the same side
            if (k.destroyed): continue
            if (k.x - FIELD_WIDTH // 2) * (pos_x - FIELD_WIDTH // 2) > 0:
                if pos_x < k.x: return True
        return False

    def enemyTankOnSameColumn(self, side: int, tank: int) -> list:
        # return enemy tank on the same column (position x is same)
        pos_x = self.tanks[side][tank].x
        pos_y = self.tanks[side][tank].y

        enemy = 1 - side
        for tank in self.tanks[enemy]:
            if not tank.destroyed and tank.x == pos_x:
                return [tank]
        return []

    def distanceToBrick(self, side: int,  tank: int) -> int:
        pos_x = self.tanks[side][tank].x
        pos_y = self.tanks[side][tank].y

        min_dis = FIELD_HEIGHT
        for y in range(FIELD_HEIGHT):
            if (self.fieldContent[y][pos_x] and self.fieldContent[y][pos_x][0].itemType == FieldItemType.Brick):
                min_dis = min(min_dis, abs(y - pos_y))
        return min_dis

    def distanceYToBase(self, side: int):
        m = 9999
        for tank in self.tanks[side]:
            m = min(m, abs(tank.y - self.bases[1-side].y))
        return m

    def numBetweenTanks(self, side: int, tank1: int, tank2:FieldObject) -> int:
        x = self.tanks[side][tank1].x
        y1 = self.tanks[side][tank1].y
        # y2 = self.tanks[1 - side][tank2].y
        y2 = tank2.y

        y_min = min(y1, y2)
        y_max = max(y1, y2)

        num = 0
        for y in range(y_min, y_max):
            if (self.fieldContent[y][x] and self.fieldContent[y][x][0].itemType == FieldItemType.Brick):
                num += 1
        return num

    def getCloserToBase(self, side: int, tank: int, action: Action) -> bool:
        if action == Action.Stay or action >= Action.UpShoot:
            return False

        target_x = self.bases[1 - side].x
        target_y = self.bases[1 - side].y
        pos_x = self.tanks[side][tank].x
        pos_y = self.tanks[side][tank].y
        x = pos_x + dx[action]
        y = pos_y + dy[action]

        if (x == FIELD_WIDTH // 2): return False
        return self._dis_between(target_x, target_y, x, y) < self._dis_between(target_x, target_y, pos_x, pos_y)

    def _dis_between(self, x1: int, y1: int, x2: int, y2: int) -> int:
        return abs(x1 - x2) + abs(y1 - y2)

    def allValid(self) -> bool:
        for tanks in self.tanks:
            for tank in tanks:
                if not tank.destroyed and not self.actionValid(tank.side, tank.tankID, self.actions[tank.side][tank.tankID]):
                    return False
        return True

    def inRange(self, x: int, y: int) -> bool:
        return x >= 0 and x < FIELD_WIDTH and y >= 0 and y < FIELD_HEIGHT

    def setActions(self, side: int, actions: List[int]) -> bool:
        if self.actionValid(side, 0, actions[0]) and self.actionValid(side, 1, actions[1]):
            self.actions[side] = actions
            return True
        return False

    def doActions(self) -> bool:
        if not self.allValid():
            return False

        self.lastactions = self.actions.copy()

        for tanks in self.tanks:
            for tank in tanks:
                action = self.actions[tank.side][tank.tankID]
                if not tank.destroyed and action >= Action.Up and action < Action.UpShoot:
                    self.removeFieldItem(tank)
                    tank.x = tank.x + dx[action]
                    tank.y = tank.y + dy[action]
                    self.insertFieldItem(tank)

        itemsToBeDestroyed = set()

        for tanks in self.tanks:
            for tank in tanks:
                action = self.actions[tank.side][tank.tankID]
                if not tank.destroyed and action >= Action.UpShoot:
                    x = tank.x
                    y = tank.y
                    action = action % 4
                    multipleTankWithMe = len(self.fieldContent[y][x]) > 1
                    while True:
                        x = x + dx[action]
                        y = y + dy[action]
                        if not self.inRange(x, y):
                            break
                        collides = self.fieldContent[y][x]
                        if collides:
                            if not multipleTankWithMe and len(collides) == 1 and collides[0].itemType == FieldItemType.Tank:
                                oppAction = self.actions[collides[0].side][collides[0].tankID]
                                if oppAction >= Action.UpShoot and action == (oppAction + 2) % 4:
                                    break
                            itemsToBeDestroyed.update(collides)
                            break

        for item in itemsToBeDestroyed:
            if item.itemType != FieldItemType.Steel:
                self.removeFieldItem(item)

        self.currentTurn = self.currentTurn + 1
        self.actions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]

    def sidelose(self, side: int) -> bool:
        return (self.tanks[side][0].destroyed and self.tanks[side][1].destroyed) or self.bases[side].destroyed

    def whowins(self) -> WhoWins:
        fail = [self.sideLose(s) for s in range(side_count)]
        if fail[0] == fail[1]:
            return WhoWins.Draw if fail[0] or self.currentTurn > 100 else WhoWins.NotFinished
        if fail[0]:
            return WhoWins.Red
        return Whowins.Blue

    def showPicture(self):
        for y in range(FIELD_HEIGHT):
            row = ""
            for x in range(FIELD_WIDTH):
                if not self.fieldContent[y][x]:
                    # print ("0 ", file=sys.stderr)
                    row = row + "0 "
                else:
                    # print (self.fieldContent[y][x][0].itemType, " ", file=sys.stderr)
                    row = row + "{} ".format(self.fieldContent[y][x][0].itemType)
            print (row, file=sys.stderr)

enemyLastActions = []

class BotzoneIO:
    def __init__(self, longRunning = False):
        self.longRunning = longRunning
        self.mySide = -1
        self.data = None
        self.globaldata = None

    def _processItem(self, field: TankField, item, isOpponent: bool):
        if isinstance(item, dict):
            self.mySide = item['mySide']
            field.fromBinary(item['field'])
        elif isOpponent:
            field.setActions(1 - self.mySide, item)
            enemyLastActions = item
            field.doActions()
        else:
            field.setActions(self.mySide, item)

    def readInput(self, field: TankField):
        string = input()
        obj = json.loads(string)
        if 'requests' in obj:
            requests = obj['requests']
            responses = obj['responses']
            n = len(requests)
            for i in range(n):
                self._processItem(field, requests[i], True)
                if i < n - 1:
                    self._processItem(field, responses[i], False)

            if 'data' in obj:
                self.data = obj['data']
            if 'globaldata' in obj:
                self.globaldata = obj['globaldata']
        else:
            self._processItem(field, obj, True)

    def writeOutput(self, actions: List[Action], debug: str = None, data: str = None, globaldata: str = None, exitAfterOutput = False):
        print(json.dumps({
            'response': actions,
            'debug': debug,
            'data': data,
            'globaldata': globaldata
        }))
        if exitAfterOutput:
            exit(0)
        else:
            print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
            sys.stdout.flush()

def is_shoot(action):
    return action in [Action.DownShoot, Action.UpShoot, Action.LeftShoot, Action.RightShoot]

# Nil = 0
# Brick = 1
# Steel = 2
# Base = 3
# Tank = 4, tanks: -1, -2, -3, -4
init_grid = [
    [1, 1, 0, 1, 3, 1, 0, 0, 0],
    [0, 0, 0, 0, 2, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 1, 0, 1, 0, 0, 0, 0, 0],
    [1, 1, 0, 1, 1, 0, 0, 1, 1],
    [0, 0, 0, 0, 1, 0, -3, 1, 1],
    [0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 1, 0, 1, 2, -1, 0, 0, 0],
    [0, 0, 0, 1, 3, -2, 0, 1, 1]
]

if __name__ == '__main__':
    field = TankField()
    io = BotzoneIO()
    lastAction = [Action.Invalid, Action.Invalid]
    while True:
        io.readInput(field)

        # io.mySide = 0
        # field.fromMatrix(init_grid)

        debug = []

        myActions = [Action.Invalid, Action.Invalid]
        destroyed = [field.tanks[1-io.mySide][0].destroyed, field.tanks[1-io.mySide][1].destroyed]

        # if we can shoot the base
        for tank in range(TANK_PER_SIDE):
            if not is_shoot(lastAction[tank]):
                r = field.canShootBase(io.mySide, tank)
                if r > 0:
                    myActions[tank] = r
                    debug.append({'tank': tank, 'shoot the base': r})

            debug.append({'scope': 'shoot base', 'tank': tank})

        # if we can shoot a tank
        for tank in range(TANK_PER_SIDE):
            if myActions[tank] == Action.Invalid:
                if not is_shoot(lastAction[tank]):
                    for target in range(TANK_PER_SIDE):
                        r = field.canShootTank(io.mySide, tank, target)
                        if not destroyed[target] and r != Action.Invalid:
                            myActions[tank] = r
                            destroyed[tank] = True
                            debug.append({'tank': tank, 'target': target, 'action': r})
                else:
                    # avoid to be shot
                    for target in range(TANK_PER_SIDE):
                        r = field.canShootTank(io.mySide, tank, target)
                        if not destroyed[target] and r != Action.Invalid:
                            if enemyLastActions and not is_shoot(enemyLastActions[target]):
                                # we will be shot
                                if field.canMove(io.mySide, tank, Action.Left):
                                    myActions[tank] = Action.Left
                                elif field.canMove(io.mySide, tank, Action.Right):
                                    myActions[tank] = Action.Right
                                else:
                                    pass # will be dicide later.
                            else:
                                myActions[tank] = Action.Down if io.mySide == 0 else Action.Up
                                if not field.canMove(io.mySide, tank, myActions[tank]):
                                    myActions[tank] = Action.Invalid
                debug.append({'scope': 'shoot tank', 'tank': tank})

        # if we can shoot beforehand
        for tank in range(TANK_PER_SIDE):
            if myActions[tank] == Action.Invalid:
                if not is_shoot(lastAction[tank]):
                    for target in range(TANK_PER_SIDE):
                        if io.mySide == 0:
                            r1 = field.canShootTankUpwards(io.mySide, tank, target)
                            r2 = field.canShootTankUpwards(io.mySide, tank, target, 2)
                        else:
                            r1 = field.canShootTankDownwords(io.mySide, tank, target)
                            r2 = field.canShootTankDownwords(io.mySide, tank, target, 2)
                        if not destroyed[tank]:
                            if r1 != Action.Invalid:
                                # here don't mark the target as destroyed, since we need avoid to be shot
                                myActions[tank] = r1
                                debug.append({'tank': tank, 'target': target, 'beforehand action': r1})
                            elif r2 != Action.Invalid and random.random() > 0.2:
                                myActions[tank] = Action.Stay # we just wait it
                                debug.append({'tank': tank, 'target': target, 'beforehand action more 1': r1})
                else:
                    for target in range(TANK_PER_SIDE):
                        if io.mySide == 0:
                            r1 = field.canShootTankUpwards(io.mySide, tank, target)
                            r2 = field.canShootTankUpwards(io.mySide, tank, target, 2)
                        else:
                            r1 = field.canShootTankDownwords(io.mySide, tank, target)
                            r2 = field.canShootTankDownwords(io.mySide, tank, target, 2)
                        if not destroyed[tank]:
                            if (r1 != Action.Invalid or r2 != Action.Invalid) and random.random() > 0.4:
                                myActions[tank] = Action.Stay # we just wait it
                                debug.append({'tank': tank, 'target': target, 'beforehand action more 2': r1})

                debug.append({'scope': 'shoot beforehand', 'tank': tank})

        # protect our base
        for tank in range(TANK_PER_SIDE):
            if myActions[tank] == Action.Invalid:
                if field.distanceYToBase(io.mySide) >= field.distanceYToBase(1-io.mySide):
                    if field.canMove(io.mySide, tank, Action.Right) and \
                            field.canShootTank(io.mySide, tank, target, 1, 0) != Action.Invalid:
                        myActions[tank] = Action.Right
                        debug.append({'protect': tank, 'direction': Action.Right})
                    elif field.canMove(io.mySide, tank, Action.Left) and \
                            field.canShootTank(io.mySide, tank, target, -1, 0) != Action.Invalid:
                        myActions[tank] = Action.Left
                        debug.append({'protect': tank, 'direction': Action.Left})

            debug.append({'scope': 'protect', 'tank': tank})

        # otherwise: avoid to be shot and move towards the base
        for tank in range(TANK_PER_SIDE):
            if myActions[tank] == Action.Invalid:
                r = field.enemyTankOnSameColumn(io.mySide, tank)
                if r:
                    dist = field.numBetweenTanks(io.mySide, tank, r[0])
                    up = field.tanks[io.mySide][tank].y > r[0].y
                    debug.append({'dist': dist, 'up': up})
                    if dist == 1: # move towards the target, OR stay
                        if up:
                            if field.canMove(io.mySide, tank, Action.Up):
                                myActions[tank] = Action.Up
                            else:
                                myActions[tank] = Action.Stay
                        else:
                            if field.canMove(io.mySide, tank, Action.Down):
                                myActions[tank] = Action.Down
                            else:
                                myActions[tank] = Action.Stay
                    else:
                        if up:
                            if not is_shoot(lastAction[tank]):
                                myActions[tank] = Action.UpShoot
                            elif field.canMove(io.mySide, tank, Action.Up):
                                myActions[tank] = Action.Up
                            else:
                                myActions[tank] = Action.Stay # TODO: we have nothing else can no
                        else:
                            if not is_shoot(lastAction[tank]):
                                myActions[tank] = Action.DownShoot
                            elif field.canMove(io.mySide, tank, Action.Down):
                                myActions[tank] = Action.Down
                            else:
                                myActions[tank] = Action.Stay # TODO: we have nothing else can no
                else:
                    # move towards the target
                    if io.mySide == 0: # move downwards
                        if field.canMove(io.mySide, tank, Action.Down):
                            myActions[tank] = Action.Down
                            debug.append({'myside': io.mySide, 'action 1': 'down'})
                        elif not is_shoot(lastAction[tank]) and field.canShot(io.mySide, tank, Action.DownShoot):
                            myActions[tank] = Action.DownShoot # hit the brick
                            debug.append({'myside': io.mySide, 'action 1': 'down shoot'})
                        elif field.canMove(io.mySide, tank, Action.Left):
                            myActions[tank] = Action.Left
                            debug.append({'myside': io.mySide, 'action 1': 'left'})
                        elif field.canMove(io.mySide, tank, Action.Right):
                            myActions[tank] = Action.Right
                            debug.append({'myside': io.mySide, 'action 1': 'right'})
                        else:
                            myActions[tank] = Action.Stay
                            debug.append({'myside': io.mySide, 'action 1': 'stay'})
                    else: # move upwards
                        if field.canMove(io.mySide, tank, Action.Up):
                            myActions[tank] = Action.Up
                            debug.append({'myside': io.mySide, 'action 2': 'up'})
                        elif not is_shoot(lastAction[tank]) and field.canShot(io.mySide, tank, Action.UpShoot):
                            myActions[tank] = Action.UpShoot # hit the brick
                            debug.append({'myside': io.mySide, 'action 2': 'up shoot'})
                        elif field.canMove(io.mySide, tank, Action.Left):
                            myActions[tank] = Action.Left
                            debug.append({'myside': io.mySide, 'action 2': 'left'})
                        elif field.canMove(io.mySide, tank, Action.Right):
                            myActions[tank] = Action.Right
                            debug.append({'myside': io.mySide, 'action 2': 'right'})
                        else:
                            myActions[tank] = Action.Stay
                            debug.append({'myside': io.mySide, 'action 2': 'stay'})

                debug.append({'scope': 'otherwise', 'tank': tank})

        # ensure we don't give invalid operation
        for tank in range(TANK_PER_SIDE):
            if myActions[tank] == Action.Invalid:
                myActions[tank] = Action.Stay # stay: for better debugging

        io.writeOutput(myActions, debug, io.data, io.globaldata, False)
        field.setActions(io.mySide, myActions)
        lastAction[0] = myActions[0]
        lastAction[1] = myActions[1]
