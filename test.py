import pygame
import random
import math

# --- 配置参数 ---
WIDTH, HEIGHT = 800, 800
CENTER = (WIDTH // 2, HEIGHT // 2)
RADIUS = 350
BALL_RADIUS = 12
LINE_THRESHOLD = 16  # 掠夺线的距离阈值
FPS = 60

# 颜色定义
COLORS = {
    "red": (255, 50, 50),
    "green": (50, 255, 50),
    "blue": (50, 100, 255),
    "yellow": (255, 255, 50),
    "white": (255, 255, 255),
    "black": (0, 0, 0)
}

class Line:
    def __init__(self, anchor_pos, owner):
        self.anchor_pos = anchor_pos  # 圆周上的固定点
        self.owner = owner            # 当前所属的球

    def draw(self, screen):
        pygame.draw.line(screen, self.owner.color, self.anchor_pos, self.owner.pos, 1)

class Ball:
    def __init__(self, color_name, pos, vel):
        self.color_name = color_name
        self.color = COLORS[color_name]
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.lines = []

    def update(self):
        self.pos += self.vel

        # 1. 碰到圆周边界反弹
        dist_to_center = self.pos.distance_to(pygame.Vector2(CENTER))
        if dist_to_center + BALL_RADIUS > RADIUS:
            # 找到碰撞点并计算法线
            normal = (self.pos - pygame.Vector2(CENTER)).normalize()
            self.vel = self.vel.reflect(normal)
            
            # 将球推回边界内防止卡住
            self.pos = pygame.Vector2(CENTER) + normal * (RADIUS - BALL_RADIUS)
            
            # 在碰撞点长出一条新线
            collision_point = pygame.Vector2(CENTER) + normal * RADIUS
            new_line = Line((collision_point.x, collision_point.y), self)
            self.lines.append(new_line)
            return True # 触发了碰撞
        return False

def get_dist_to_line(p, a, b):
    """计算点 p 到线段 ab 的距离"""
    ap = p - a
    ab = b - a
    result = ap.dot(ab) / ab.length_squared()
    if result < 0:
        closest = a
    elif result > 1:
        closest = b
    else:
        closest = a + ab * result
    return p.distance_to(closest)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("小球掠夺战")
    clock = pygame.time.Clock()

    # 初始化 4 个球
    balls = []
    ball_configs = [("red", (350, 350)), ("green", (450, 350)), ("blue", (350, 450)), ("yellow", (450, 450))]
    
    for color, pos in ball_configs:
        vel = (random.uniform(-3, 3), random.uniform(-3, 3))
        ball = Ball(color, pos, vel)
        
        # 初始 3 根线，连向运动方向前方的圆周
        angle = math.atan2(vel[1], vel[0])
        for i in range(-1, 2):
            line_angle = angle + i * 0.5
            target = pygame.Vector2(CENTER) + pygame.Vector2(math.cos(line_angle), math.sin(line_angle)) * RADIUS
            ball.lines.append(Line((target.x, target.y), ball))
        balls.append(ball)

    running = True
    while running:
        screen.fill(COLORS["black"])
        
        # 画大圆背景
        pygame.draw.circle(screen, COLORS["white"], CENTER, RADIUS, 2)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 存储所有线段用于检测掠夺
        all_lines = []
        for b in balls:
            all_lines.extend(b.lines)

        # 更新球的位置与碰撞
        for i, ball in enumerate(balls):
            ball.update()

            # 球与球之间的碰撞
            for other in balls[i+1:]:
                if ball.pos.distance_to(other.pos) < BALL_RADIUS * 2:
                    ball.vel, other.vel = other.vel, ball.vel # 简单交换速度模拟碰撞

            # 掠夺逻辑
            for line in all_lines:
                if line.owner != ball:
                    # 如果球靠近别人的线
                    d = get_dist_to_line(ball.pos, pygame.Vector2(line.anchor_pos), line.owner.pos)
                    if d < LINE_THRESHOLD:
                        # 换主人
                        line.owner.lines.remove(line)
                        line.owner = ball
                        ball.lines.append(line)

        # 绘制
        for ball in balls:
            for line in ball.lines:
                line.draw(screen)
            pygame.draw.circle(screen, ball.color, (int(ball.pos.x), int(ball.pos.y)), BALL_RADIUS)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()