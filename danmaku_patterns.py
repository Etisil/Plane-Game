import math
import random
import pygame


SCREEN_RECT = pygame.Rect(0, 0, 480, 700)
BOSS_BULLET_RADIUS = 6

DANMAKU_COLORS = {
    "red": (255, 115, 125),
    "orange": (255, 185, 95),
    "blue": (115, 190, 255),
    "green": (125, 255, 155),
    "purple": (220, 135, 255),
    "cyan": (115, 255, 255),
    "yellow": (255, 245, 115),
    "pink": (255, 155, 215),
    "white": (255, 255, 255),
}


class DanmakuBullet(pygame.sprite.Sprite):
    """敌方弹幕子弹，使用浮点速度保证弹道更平滑。"""

    def __init__(self, color, radius, speed, angle, x, y):
        """创建统一尺寸的 Boss 弹幕，并按颜色选择视觉样式。"""
        super().__init__()
        self.color = DANMAKU_COLORS.get(color, color)
        self.radius = BOSS_BULLET_RADIUS
        self.speed = speed
        self.angle = angle
        self.speedx = math.cos(angle) * speed
        self.speedy = math.sin(angle) * speed
        self.life = 360
        self.harmful = True
        self.float_x = float(x)
        self.float_y = float(y)
        self.style = self.__select_style(color)
        self.rotation = 0
        self.rotation_speed = 6 if self.style == "ellipse" else 0
        self.base_image = self.__make_image()
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(round(self.float_x), round(self.float_y)))

    @staticmethod
    def __select_style(color):
        """根据颜色稳定选择实心、空心或椭圆子弹样式。"""
        if color in ("blue", "cyan", "green"):
            return "hollow"
        if color in ("purple", "pink", "white"):
            return "ellipse"
        return "solid"

    def __make_image(self):
        """绘制无外白圈的基础弹幕图像。"""
        size = BOSS_BULLET_RADIUS * 2 + 4
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        if self.style == "hollow":
            pygame.draw.circle(image, (255, 255, 255), center, max(2, BOSS_BULLET_RADIUS - 2))
            pygame.draw.circle(image, self.color, center, BOSS_BULLET_RADIUS, 2)
        elif self.style == "ellipse":
            rect = pygame.Rect(0, 0, BOSS_BULLET_RADIUS * 2 + 2, BOSS_BULLET_RADIUS + 3)
            rect.center = center
            pygame.draw.ellipse(image, self.color, rect)
            pygame.draw.ellipse(image, (255, 255, 255, 110), rect.inflate(-5, -4))
        else:
            pygame.draw.circle(image, self.color, center, BOSS_BULLET_RADIUS)
            pygame.draw.circle(image, (255, 255, 255, 95), center, 2)
        return image

    def update(self):
        """按浮点速度移动子弹，并在需要时旋转椭圆样式。"""
        self.float_x += self.speedx
        self.float_y += self.speedy
        center = (round(self.float_x), round(self.float_y))
        if self.rotation_speed:
            self.rotation = (self.rotation + self.rotation_speed) % 360
            self.image = pygame.transform.rotate(self.base_image, self.rotation)
            self.rect = self.image.get_rect(center=center)
        else:
            self.rect.center = center
        self.life -= 1

        live_area = SCREEN_RECT.inflate(120, 120)
        if self.life <= 0 or not live_area.colliderect(self.rect):
            self.kill()

    @staticmethod
    def create_bullet_pool():
        """预留对象池接口，当前仍按普通 Sprite 生命周期创建。"""
        return []


class LaserBeam(pygame.sprite.Sprite):
    """带预警帧的可旋转激光，使用线段距离做更准确的碰撞判定。"""

    def __init__(self, x, y, width=56, length=SCREEN_RECT.height, warning_frames=35, active_frames=70,
                 color="red", angle=math.pi / 2):
        """创建一条从起点按角度延伸的预警/伤害激光。"""
        super().__init__()
        self.color = DANMAKU_COLORS.get(color, DANMAKU_COLORS["red"])
        self.width = width
        self.length = length
        self.warning_frames = warning_frames
        self.active_frames = active_frames
        self.timer = 0
        self.harmful = False
        self.angle = angle
        self.start = (float(x), float(y))
        self.end = (float(x + math.cos(angle) * length), float(y + math.sin(angle) * length))
        self.__build_surface()
        self.__refresh_image()

    def __build_surface(self):
        """按激光线段包围盒创建透明绘制 Surface。"""
        padding = self.width + 16
        left = min(self.start[0], self.end[0]) - padding
        top = min(self.start[1], self.end[1]) - padding
        right = max(self.start[0], self.end[0]) + padding
        bottom = max(self.start[1], self.end[1]) + padding
        self.rect = pygame.Rect(round(left), round(top), max(1, round(right - left)), max(1, round(bottom - top)))
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.local_start = (self.start[0] - self.rect.left, self.start[1] - self.rect.top)
        self.local_end = (self.end[0] - self.rect.left, self.end[1] - self.rect.top)

    def __refresh_image(self):
        """根据预警或伤害阶段刷新激光颜色和可伤害状态。"""
        self.image.fill((0, 0, 0, 0))
        if self.timer < self.warning_frames:
            alpha = 100 if (self.timer // 6) % 2 else 185
            pygame.draw.line(self.image, (255, 25, 25, alpha), self.local_start, self.local_end, 5)
            pygame.draw.line(self.image, (255, 120, 120, alpha), self.local_start, self.local_end, 2)
            self.harmful = False
        else:
            self.harmful = True
            pygame.draw.line(self.image, (*self.color, 130), self.local_start, self.local_end, self.width)
            pygame.draw.line(self.image, (*self.color, 230), self.local_start, self.local_end, max(8, self.width // 2))
            pygame.draw.line(self.image, (255, 255, 255, 245), self.local_start, self.local_end, max(4, self.width // 5))

    def update(self):
        """推进激光计时，到期自动销毁。"""
        self.timer += 1
        if self.timer >= self.warning_frames + self.active_frames:
            self.kill()
            return
        self.__refresh_image()

    def collides_with(self, target_rect):
        """使用点到线段距离判断玩家判定框是否被激光击中。"""
        if not self.harmful:
            return False

        px, py = target_rect.center
        ax, ay = self.start
        bx, by = self.end
        dx = bx - ax
        dy = by - ay
        segment_length_sq = dx * dx + dy * dy
        if segment_length_sq <= 0:
            return False

        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / segment_length_sq))
        nearest_x = ax + t * dx
        nearest_y = ay + t * dy
        distance_sq = (px - nearest_x) ** 2 + (py - nearest_y) ** 2
        hit_radius = self.width / 2 + max(target_rect.width, target_rect.height) / 2
        return distance_sq <= hit_radius * hit_radius


class DelayedAimedBullet(DanmakuBullet):
    """先停在几何阵列中展示，再朝生成时锁定的玩家方向飞出。"""

    def __init__(self, color, radius, speed, x, y, target_x, target_y, hold_frames=60):
        """创建先停留展示、随后朝玩家当前位置直线飞行的子弹。"""
        angle = math.atan2(target_y - y, target_x - x)
        super().__init__(color, radius, 0, angle, x, y)
        self.launch_speed = speed
        self.hold_frames = hold_frames
        self.timer = 0
        self.harmful = False

    def update(self):
        """停留阶段闪烁，达到延迟后锁定方向发射。"""
        self.timer += 1
        if self.timer >= self.hold_frames and self.speed == 0:
            self.speed = self.launch_speed
            self.speedx = math.cos(self.angle) * self.speed
            self.speedy = math.sin(self.angle) * self.speed
            self.harmful = True

        if self.timer < self.hold_frames:
            if self.timer % 12 < 6:
                pulse_image = self.image.copy()
                pulse_image.fill((80, 80, 80), special_flags=pygame.BLEND_RGB_ADD)
                self.image = pulse_image

        super().update()


class DanmakuPattern(object):
    """经典弹幕模式生成器。"""

    @staticmethod
    def circle(center_x, center_y, bullet_count=24, radius=20, speed=2, color="red", angle_offset=0):
        """生成一圈径向扩散子弹。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            bullets.append(DanmakuBullet(color, 8, speed, angle, x, y))
        return bullets

    @staticmethod
    def fan(center_x, center_y, bullet_count=9, angle_span=90, speed=2.5, color="blue", direction_angle=math.pi / 2):
        """按指定方向生成扇形弹幕。"""
        bullets = []
        span = math.radians(angle_span)
        start_angle = direction_angle - span / 2
        step = span / max(1, bullet_count - 1)
        for i in range(bullet_count):
            angle = start_angle + step * i
            bullets.append(DanmakuBullet(color, 8, speed, angle, center_x, center_y))
        return bullets

    @staticmethod
    def aimed(center_x, center_y, bullet_count=5, speed=2.8, color="cyan", target_x=SCREEN_RECT.centerx,
              target_y=SCREEN_RECT.bottom):
        """生成指向玩家的自机狙弹幕。"""
        bullets = []
        base_angle = math.atan2(target_y - center_y, target_x - center_x)
        random_offset = math.radians(random.uniform(-5, 5))
        spread = math.radians(8)
        start_angle = base_angle - spread * (bullet_count - 1) / 2
        for i in range(bullet_count):
            angle = start_angle + spread * i + random_offset
            bullets.append(DanmakuBullet(color, 8, speed, angle, center_x, center_y))
        return bullets

    @staticmethod
    def spiral(center_x, center_y, bullet_count_per_round=5, speed=2.2, color="purple", angular_velocity=0.05,
               current_angle=0):
        """按当前角度生成一轮螺旋弹幕。"""
        bullets = []
        for i in range(bullet_count_per_round):
            angle = current_angle + 2 * math.pi * i / bullet_count_per_round
            bullets.append(DanmakuBullet(color, 8, speed, angle, center_x, center_y))
        return bullets

    @staticmethod
    def double_circle(center_x, center_y, bullet_count=14, speed=2.0, color_outer="blue", color_inner="cyan",
                      angle_offset=0):
        """生成内外两层反向圆环弹幕。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            x = center_x + math.cos(angle) * 30
            y = center_y + math.sin(angle) * 30
            bullets.append(DanmakuBullet(color_outer, 7, speed, angle, x, y))

        inner_count = max(4, bullet_count // 2)
        for i in range(inner_count):
            angle = 2 * math.pi * i / inner_count - angle_offset
            x = center_x + math.cos(angle) * 16
            y = center_y + math.sin(angle) * 16
            bullets.append(DanmakuBullet(color_inner, 6, speed * 1.15, angle + math.pi, x, y))
        return bullets

    @staticmethod
    def butterfly(center_x, center_y, bullet_count=24, speed=1.8, color="purple", angle_offset=0):
        """生成带横向波动的蝶形弹幕。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            wave = math.sin(i * 0.55 + angle_offset) * 1.2
            bullet = DanmakuBullet(color, 6, speed, angle, center_x, center_y)
            bullet.speedx = (math.cos(angle) * speed + wave) * 0.9
            bullet.speedy = math.sin(angle) * speed * 0.95
            bullets.append(bullet)
        return bullets

    @staticmethod
    def cross(center_x, center_y, bullet_count_per_line=8, speed=2.2, color="cyan", angle_offset=0):
        """生成交叉轴向弹幕。"""
        bullets = []
        for base in (0, math.pi / 2):
            for i in range(bullet_count_per_line):
                angle = base + math.pi * i / bullet_count_per_line + angle_offset
                bullets.append(DanmakuBullet(color, 7, speed, angle, center_x, center_y))
        return bullets

    @staticmethod
    def chrysanthemum(center_x, center_y, bullet_count=12, layers=3, speed=1.5, colors=("red", "pink", "white"),
                      angle_offset=0):
        """生成多层菊花状环形弹幕。"""
        bullets = []
        for layer in range(layers):
            count = bullet_count + layer * 4
            color = colors[layer % len(colors)]
            for i in range(count):
                angle = 2 * math.pi * i / count + angle_offset + layer * 0.18
                x = center_x + math.cos(angle) * (18 + layer * 15)
                y = center_y + math.sin(angle) * (18 + layer * 15)
                bullets.append(DanmakuBullet(color, 5 + layer, speed + layer * 0.35, angle, x, y))
        return bullets

    @staticmethod
    def star(center_x, center_y, bullet_count=20, speed=2.0, color="yellow", angle_offset=0):
        """按星形顶点生成外扩弹幕。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            radius = 56 if i % 2 == 0 else 24
            x_offset = math.cos(angle) * radius
            y_offset = math.sin(angle) * radius * 0.75
            fire_angle = math.atan2(y_offset, x_offset)
            bullets.append(DanmakuBullet(color, 7, speed, fire_angle, center_x + x_offset, center_y + y_offset))
        return bullets

    @staticmethod
    def kaleidoscope(center_x, center_y, bullet_count=32, speed=1.6,
                     colors=("red", "orange", "yellow", "green", "cyan", "blue", "purple"), angle_offset=0):
        """生成多色万花镜环形弹幕。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            color = colors[i % len(colors)]
            radius = 12 + (i % 5) * 8
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            bullets.append(DanmakuBullet(color, 6, speed + (i % 3) * 0.35, angle, x, y))
        return bullets

    @staticmethod
    def yin_yang(center_x, center_y, bullet_count=18, speed=1.8, angle_offset=0):
        """生成黑白交替的阴阳环弹幕。"""
        bullets = []
        for i in range(bullet_count):
            angle = 2 * math.pi * i / bullet_count + angle_offset
            color = "white" if i % 2 == 0 else "purple"
            radius = 7 if i % 2 == 0 else 5
            offset = 16 if i % 2 == 0 else 28
            x = center_x + math.cos(angle) * offset
            y = center_y + math.sin(angle) * offset
            bullets.append(DanmakuBullet(color, radius, speed, angle, x, y))
        return bullets

    @staticmethod
    def ordered_aimed_ring(center_x, center_y, target_x, target_y, frame, total_bullets=28, ring_radius=72,
                           spawn_interval=3, speed=3.0, color="pink", angle_offset=0):
        """逐颗在环上生成子弹，展示后统一朝玩家锁定方向飞出。"""
        bullets = []
        cycle = total_bullets * spawn_interval + 70
        local_frame = frame % cycle
        if local_frame >= total_bullets * spawn_interval:
            return bullets

        if local_frame % spawn_interval != 0:
            return bullets

        idx = local_frame // spawn_interval
        angle = 2 * math.pi * idx / total_bullets + angle_offset
        x = center_x + math.cos(angle) * ring_radius
        y = center_y + math.sin(angle) * ring_radius
        hold_frames = (total_bullets - idx) * spawn_interval + 12
        bullets.append(DelayedAimedBullet(color, 7, speed, x, y, target_x, target_y, hold_frames))
        return bullets

    @staticmethod
    def spiral_staircase(center_x, center_y, frame, bullet_count=60, speed=2.0, color="cyan"):
        """按黄金角生成双臂螺旋阶梯弹幕。"""
        bullets = []
        if frame % 2 != 0:
            return bullets

        golden_angle = math.pi * (3 - math.sqrt(5))
        idx = (frame // 2) % bullet_count
        for offset in (0, bullet_count // 2):
            i = (idx + offset) % bullet_count
            t = i / bullet_count
            angle = i * golden_angle
            radius = 12 + t * 110
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            bullets.append(DanmakuBullet(color, 6, speed + t * 0.6, angle + math.pi / 2, x, y))
        return bullets

    @staticmethod
    def kaleidoscope_mirror(center_x, center_y, frame, symmetry=6, bullet_count_per_axis=3, radius=68, speed=2.3):
        """生成多轴对称的万花镜镜像弹幕。"""
        bullets = []
        if frame % 10 != 0:
            return bullets

        base_offset = frame * 0.018
        for axis in range(symmetry):
            axis_angle = 2 * math.pi * axis / symmetry + base_offset
            for side in (-1, 1):
                for dist in range(1, bullet_count_per_axis + 1):
                    angle = axis_angle + side * dist * 0.12
                    r = radius * (dist / bullet_count_per_axis)
                    x = center_x + math.cos(angle) * r
                    y = center_y + math.sin(angle) * r
                    color = ("cyan", "blue", "purple")[dist - 1]
                    bullets.append(DanmakuBullet(color, 5 + dist, speed * (0.8 + dist * 0.12), angle, x, y))
        return bullets

    @staticmethod
    def sine_wave_wall(center_x, center_y, frame, bullets_per_wall=18, amplitude=38, speed=2.1, color="green"):
        """生成从上方向下推进的正弦波墙。"""
        bullets = []
        if frame % 24 != 0:
            return bullets

        phase_offset = frame * 0.04
        for i in range(bullets_per_wall):
            x_ratio = i / max(1, bullets_per_wall - 1)
            x = SCREEN_RECT.left + 36 + x_ratio * (SCREEN_RECT.width - 72)
            y = center_y + 20 + math.sin(2 * math.pi * x_ratio * 2 + phase_offset) * amplitude
            if 0 < y < SCREEN_RECT.height:
                bullets.append(DanmakuBullet(color, 6, speed, math.pi / 2, x, y))
        return bullets

    @staticmethod
    def hexagram_array(center_x, center_y, frame, star_radius=82, speed=2.1):
        """逐点生成六芒星结构弹幕。"""
        bullets = []
        if frame % 4 != 0:
            return bullets

        idx = (frame // 4) % 12
        if idx % 2 == 0:
            angle = 2 * math.pi * (idx // 2) / 6
            radius = star_radius
            color = "orange"
            bullet_size = 8
        else:
            angle = 2 * math.pi * (idx // 2) / 6 + math.pi / 6
            radius = star_radius * 0.58
            color = "yellow"
            bullet_size = 6

        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius
        bullets.append(DanmakuBullet(color, bullet_size, speed, angle, x, y))
        if idx == 0:
            bullets.append(DanmakuBullet("white", 10, 1.25, math.pi / 2, center_x, center_y))
        return bullets

    @staticmethod
    def rotating_multi_directional(center_x, center_y, frame, directions=6, bullets_per_direction=2,
                                   rotation_speed=0.025, speed=2.3, color="cyan", spread_angle=10):
        """生成多方向同时旋转发射的星形弹幕。"""
        bullets = []
        rotation = frame * rotation_speed
        spread = math.radians(spread_angle)
        for direction in range(directions):
            base_angle = 2 * math.pi * direction / directions + rotation
            for index in range(bullets_per_direction):
                offset = 0
                if bullets_per_direction > 1:
                    offset = (index - (bullets_per_direction - 1) / 2) * spread / bullets_per_direction
                bullets.append(DanmakuBullet(color, 6, speed + index * 0.12,
                                             base_angle + offset, center_x, center_y))
        return bullets

    @staticmethod
    def breathing_cluster(center_x, center_y, frame, bullet_count=28, cluster_radius=58,
                          breathe_speed=0.025, move_width=30, color="pink", radius_variation=20,
                          speed=1.45):
        """生成整体呼吸缩放并缓慢漂移的环形弹幕簇。"""
        bullets = []
        breathe_phase = frame * breathe_speed
        current_radius = cluster_radius + math.sin(breathe_phase) * radius_variation
        offset_x = math.sin(frame * 0.012) * move_width
        offset_y = math.cos(frame * 0.008) * move_width * 0.45

        for index in range(bullet_count):
            angle = 2 * math.pi * index / bullet_count
            x = center_x + offset_x + math.cos(angle) * current_radius
            y = center_y + offset_y + math.sin(angle) * current_radius
            fire_angle = angle + math.sin(breathe_phase + index * 0.18) * 0.08
            radius = 5 + int(abs(math.sin(breathe_phase + index * 0.2)) * 3)
            bullets.append(DanmakuBullet(color, radius, speed, fire_angle, x, y))
        return bullets

    @staticmethod
    def gear_array(center_x, center_y, frame, inner_count=12, outer_count=18,
                   inner_radius=38, outer_radius=78, speed=1.9,
                   color_inner="blue", color_outer="cyan"):
        """生成内外反向旋转的齿轮状弹幕。"""
        bullets = []
        inner_rotation = frame * 0.025
        outer_rotation = -frame * 0.018

        for index in range(inner_count):
            angle = 2 * math.pi * index / inner_count + inner_rotation
            x = center_x + math.cos(angle) * inner_radius
            y = center_y + math.sin(angle) * inner_radius
            bullets.append(DanmakuBullet(color_inner, 5, speed * 0.9,
                                         angle + math.sin(angle + inner_rotation) * 0.25, x, y))

        for index in range(outer_count):
            angle = 2 * math.pi * index / outer_count + outer_rotation
            x = center_x + math.cos(angle) * outer_radius
            y = center_y + math.sin(angle) * outer_radius
            bullets.append(DanmakuBullet(color_outer, 7, speed * 1.08,
                                         angle + math.sin(angle + outer_rotation) * 0.18, x, y))
        return bullets

    @staticmethod
    def spiral_petal(center_x, center_y, frame, petal_count=5, bullets_per_petal=14,
                     petal_length=96, rotation_speed=0.014, speed=1.75, color="purple"):
        """逐颗生成螺旋花瓣形弹幕。"""
        bullets = []
        spawn_rate = 3
        total_bullets = petal_count * bullets_per_petal
        start_index = (frame * spawn_rate) % total_bullets
        for offset in range(spawn_rate):
            idx = (start_index + offset) % total_bullets
            petal_index = idx % petal_count
            position = idx // petal_count
            t = position / max(1, bullets_per_petal - 1)
            petal_angle = 2 * math.pi * petal_index / petal_count + frame * rotation_speed
            offset_angle = (t - 0.5) * 0.65
            radius = t * petal_length
            x = center_x + math.cos(petal_angle + offset_angle) * radius
            y = center_y + math.sin(petal_angle + offset_angle) * radius
            fire_angle = petal_angle + math.sin(t * math.pi * 2) * 0.2
            bullets.append(DanmakuBullet(color, 5 + int(t * 3), speed + t * 0.45,
                                         fire_angle, x, y))
        return bullets

    @staticmethod
    def shrinking_trap_ring(center_x, center_y, frame, bullet_count=36, max_radius=170,
                            min_radius=30, rotation_speed=0.017, color="orange",
                            ring_life=170):
        """从 Boss 附近小范围生成，并按环形方向向外扩散。"""
        bullets = []
        life_progress = (frame % ring_life) / ring_life
        current_radius = min_radius + (max_radius - min_radius) * life_progress
        rotation = frame * rotation_speed
        spawn_count = 3

        for offset in range(spawn_count):
            idx = ((frame // 2) * spawn_count + offset) % bullet_count
            angle = 2 * math.pi * idx / bullet_count + rotation
            spawn_radius = min(16, current_radius)
            x = center_x + math.cos(angle) * spawn_radius
            y = center_y + math.sin(angle) * spawn_radius
            speed_adj = 1.15 + life_progress * 0.7
            bullets.append(DanmakuBullet(color, BOSS_BULLET_RADIUS, speed_adj, angle, x, y))
        return bullets

    @staticmethod
    def domino_wave(center_x, center_y, frame, row_count=7, col_count=11,
                    spacing=30, speed=2.0):
        """按网格行依次生成多米诺波浪弹幕。"""
        bullets = []
        row = (frame // 4) % row_count
        direction = 1 if (frame // (row_count * 4)) % 2 == 0 else -1
        row = row if direction > 0 else row_count - 1 - row
        row_offset = spacing * 0.5 if row % 2 else 0

        for col in range(col_count):
            x = center_x - (col_count - 1) * spacing / 2 + col * spacing + row_offset
            y = center_y - 80 + row * spacing
            wave_angle = math.atan2(direction * 0.3, (col - col_count / 2) * 0.1)
            color = ("green", "cyan", "blue")[row % 3]
            bullets.append(DanmakuBullet(color, 6, speed * (0.85 + row * 0.04),
                                         math.pi / 2 + wave_angle * 0.45, x, y))
        return bullets

    @staticmethod
    def rotating_stargate(center_x, center_y, frame, layers=4, bullets_per_layer=22,
                          base_radius=30, radius_step=24,
                          rotation_speeds=(0.034, -0.025, 0.018, -0.012),
                          colors=("red", "orange", "yellow", "white"), speed=1.85):
        """生成多层同心环轮流旋转的星门弹幕。"""
        bullets = []
        layer = (frame // 6) % layers
        for index in range(bullets_per_layer):
            angle = 2 * math.pi * index / bullets_per_layer + frame * rotation_speeds[layer]
            radius = base_radius + layer * radius_step
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            bullets.append(DanmakuBullet(colors[layer % len(colors)], 5 + layer,
                                         speed * (0.85 + layer * 0.1),
                                         angle + math.pi / 2 + rotation_speeds[layer] * 0.5, x, y))
        return bullets

    @staticmethod
    def dna_helix(center_x, center_y, frame, helix_length=120, helix_radius=48,
                  bullets_per_turn=16, turns=2, speed=1.55, color1="cyan", color2="blue"):
        """生成双螺旋 DNA 结构弹幕。"""
        bullets = []
        total_steps = bullets_per_turn * turns
        progress = (frame * 0.5) % total_steps
        for chain in range(2):
            phase_offset = chain * math.pi
            t = progress / total_steps
            spiral_angle = 2 * math.pi * t * turns + phase_offset
            x = center_x + math.cos(spiral_angle) * helix_radius
            y = center_y + t * helix_length - helix_length / 2
            fire_angle = math.atan2(helix_length / total_steps,
                                    -math.sin(spiral_angle) * helix_radius * 2 * math.pi * turns)
            bullets.append(DanmakuBullet(color1 if chain == 0 else color2, 6 if chain == 0 else 5,
                                         speed * (1 + t * 0.18), fire_angle + math.pi / 2, x, y))
        return bullets

    @staticmethod
    def petal_unfolding(center_x, center_y, frame, petal_count=8, bullets_per_petal=6,
                        max_length=90, rotation_speed=0.006, color="pink"):
        """逐颗生成向外展开的花瓣弹幕。"""
        bullets = []
        total_bullets = petal_count * bullets_per_petal
        idx = frame % total_bullets
        petal_index = idx // bullets_per_petal
        position = idx % bullets_per_petal
        unfold_progress = ((frame // total_bullets) % 4 + 1) / 4
        t = (position + 1) / bullets_per_petal
        petal_angle = 2 * math.pi * petal_index / petal_count + frame * rotation_speed
        radius = t * max_length * unfold_progress
        offset_angle = (t - 0.5) * 0.25
        x = center_x + math.cos(petal_angle + offset_angle) * radius
        y = center_y + math.sin(petal_angle + offset_angle) * radius
        color_shade = "white" if position % 3 == 1 else color
        bullets.append(DanmakuBullet(color_shade, 5 + position % 3, 1.25 + t * 0.75,
                                     petal_angle + math.sin(t * math.pi * 0.5) * 0.15, x, y))
        return bullets

    @staticmethod
    def waterwheel(center_x, center_y, frame, spoke_count=8, bullets_per_spoke=5,
                   wheel_radius=62, rotation_speed=0.03, speed=2.1, color="cyan"):
        """沿旋转辐条生成水轮状弹幕。"""
        bullets = []
        spoke_index = frame % spoke_count
        spoke_angle = 2 * math.pi * spoke_index / spoke_count + frame * rotation_speed
        for index in range(bullets_per_spoke):
            t = (index + 1) / bullets_per_spoke
            radius = t * wheel_radius
            x = center_x + math.cos(spoke_angle) * radius
            y = center_y + math.sin(spoke_angle) * radius
            fire_angle = spoke_angle + math.atan2(0.3 + t * 0.2, 0.7)
            bullets.append(DanmakuBullet(color, 5 + index % 3, speed * (0.75 + t * 0.55),
                                         fire_angle, x, y))
        return bullets
