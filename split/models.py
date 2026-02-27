
class Snake:
    def __init__(self, name, body, health, id=None):
        self.id = id
        self.name = name
        self.body = body
        self.health = health
        self.length = len(body)
        self.head = body[0]
        self.neck = body[1]
        self.tail = body[-1]
        self.allowed_moves = None
        self.ngroup = None
        self.territory = None
        self.head_space = None
        self.cut_set = None
        self.cut_space = None
        self.next = None
    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body", "id", ]}
    def copy(self):
        snake = Snake(self.name, [c for c in self.body], self.health)
        snake.allowed_moves = [a for a in self.allowed_moves]
        snake.territory = [a for a in self.territory]
        snake.head_space = [a for a in self.head_space]
    def set_id(self, id):
        self.id = id
        return self

class GameTurn:
    def __init__(self):
        self.id = None
        self.state = None
        self.me: Snake = None
        self.other: Snake = None
        self.others: list[Snake] = None
        self.snakes: list[Snake] = None
        self.food = None
        self.next_coord = None
        self.occupied_cells = None
        self.log = {}
        self.decision_path = []
        self.target_snake: Snake = None
        self.max_cut_length = 8
        self.turn = None
        self.vulnerables = []

        self.start_time: float = None
        self.end_time: float = None
        self.timeout_threshold: int = 300
        self.timeout = False
        self.timing_threshold: int = 30
        self.timeout_at: str = None

