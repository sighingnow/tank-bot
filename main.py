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
    def __init__(self, side: int, tankID: int):
        super().__init__(6 if side ^ tankID else 2, side * 8, FieldItemType.Tank)
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

    def actionValid(self, side: int, tank: int, action: Action) -> bool:
        if action >= Action.UpShoot and self.lastActions[side][tank] >= Action.UpShoot:
            return False
        if action == Action.Stay or action >= Action.UpShoot:
            return True
        x = self.tanks[side][tank].x + dx[action]
        y = self.tanks[side][tank].y + dy[action]
        return self.inRange(x, y) and not self.fieldContent[y][x]

    def enemyTankOnSameColumn(self, side: int, tank: int) -> list:
        # return enemy tank on the same column (position x is same)
        pos_x = self.tanks[side][tank].x
        pos_y = self.tanks[side][tank].y

        enemy = 1 - side
        for tank in self.tanks[enemy]:
            if tank.x == pos_x:
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

if __name__ == '__main__':
    field = TankField()
    io = BotzoneIO()
    lastAction = [-9999, -9999]
    while True:
        io.readInput(field)

        myActions = []

        for tank in range(TANK_PER_SIDE):
            enemyTankOnSameColumn = field.enemyTankOnSameColumn(io.mySide, tank)
            if not enemyTankOnSameColumn:
                if field.distanceToBrick(io.mySide, tank) == 1:
                    if io.mySide == 0:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Down)
                        else:
                            myActions.append(Action.DownShoot)
                    elif io.mySide == 1:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Up)
                        else:
                            myActions.append(Action.UpShoot)
                else:
                    availableActions = [
                        action for action in range(Action.Stay, Action.LeftShoot + 1) \
                                 if field.actionValid(io.mySide, tank, action) and field.getCloserToBase(io.mySide, tank, action)
                    ]
                    myActions.append(random.choice(availableActions))
            else:
                numOfBricks = field.numBetweenTanks(io.mySide, tank, enemyTankOnSameColumn[0])
                if numOfBricks == 0:
                    if io.mySide == 0:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Left)
                        else:
                            myActions.append(Action.DownShoot)
                    else:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Right)
                        else:
                            myActions.append(Action.UpShoot)
                elif numOfBricks > 1:
                    if io.mySide == 0:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Down)
                        else:
                            myActions.append(Action.DownShoot)
                    else:
                        if lastAction[tank] in [Action.DownShoot, Action.UpShoot]:
                            myActions.append(Action.Up)
                        else:
                            myActions.append(Action.UpShoot)
                else:
                    availableActions = [
                        action for action in range(Action.Stay, Action.LeftShoot + 1) \
                                 if field.actionValid(io.mySide, tank, action) and field.getCloserToBase(io.mySide, tank, action)
                    ]
                    availableActions.append(Action.Stay)
                    myActions.append(random.choice(availableActions))

        io.writeOutput(myActions, "DEBUG!", io.data, io.globaldata, False)
        field.setActions(io.mySide, myActions)
        lastAction[0] = myActions[0]
        lastAction[1] = myActions[1]
