import math
import random
import pygame
from danmaku_patterns import DanmakuBullet, LaserBeam, DanmakuPattern
pygame.init()


# 分数
SCORE = 0


def reset_score():
    """开始新局时清空全局分数。"""
    global SCORE
    SCORE = 0
# 屏幕大小的常量
SCREEN_RECT = pygame.Rect(0, 0, 480, 700)
# color
color_blue = (30, 144, 255)
color_green = (0, 255, 0)
color_red = (255, 0, 0)
color_purple = (148, 0, 211)
color_gray = (251, 255, 242)
# 刷新的帧率
FRAME_PER_SEC = 60  # 刷新率是60hz,即每秒update60次
HERO_HIT_FLASH_MS = 100
HERO_SCALE = 0.4
HERO_HITBOX_SCALE = 0.15
HERO_FOCUS_HITBOX_SIZE = 5
HERO_BULLET_SPEED = -8
MAX_BULLET_LEVEL = 4
BULLET_LEVEL_DAMAGE = (1.0, 0.55, 0.45, 0.35)
BOSS_PHASE_COUNT = 5
BOSS_PHASE_HP = (100, 130, 140, 180, 220)
BOSS_PHASE_BREAK_FRAMES = 90
BOSS_PHASE_FILL_FRAMES = 90
DIFFICULTY_HERO_HP = {
    "normal": 24,
    "hard": 20,
    "lunatic": 12,
}

#BOSS弹幕发射间隔系数
BOSS_INTERVAL_SCALE = {
    "normal": 2.1,
    "hard": 1.7,
    "lunatic": 1.0,
}
BOSS_FULLSCREEN_INTERVAL_SCALE = {
    "normal": 1.3,
    "hard": 1.1,
    "lunatic": 1.0,
}
# 创建敌机的定时器常量,自定义用户事件，不同数表示不同事件
CREATE_ENEMY_EVENT = pygame.USEREVENT
# 英雄发射子弹事件
HERO_FIRE_EVENT = pygame.USEREVENT + 1
# buff1 出现的事件
BUFF1_SHOW_UP = pygame.USEREVENT + 2
# buff2
BUFF2_SHOW_UP = pygame.USEREVENT + 3
# 敌军发射子弹
ENEMY_FIRE_EVENT = pygame.USEREVENT + 4
# 发射炸弹
BOMB_THROW = pygame.USEREVENT + 5


class GameScore(object):
    global SCORE

    def __init__(self):
        """初始化分数读取对象。"""
        self.score = 0
        pass

    def getvalue(self):
        """返回当前全局分数。"""
        self.score = SCORE
        return self.score


class GameSprite(pygame.sprite.Sprite):
    """飞机大战游戏精灵"""

    def __init__(self, image_name, speedy=1, speedx=0):
        """加载图片并初始化基础速度、碰撞框和血条。"""
        # 调用父类的初始化方法
        super().__init__()

        # 定义对象的属性
        self.image = pygame.image.load(image_name)
        self.rect = self.image.get_rect()
        self.speedy = speedy
        self.speedx = speedx
        self.injury = 1
        self.index = 0  # 记帧数变量
        self.bar = bloodline(color_blue, self.rect.x, self.rect.y - 10, self.rect.width)

    def update(self):
        """按速度移动基础精灵并同步血条位置。"""
        # 在屏幕的垂直方向上移动
        self.rect.y += self.speedy
        self.rect.x += self.speedx
        self.bar.x = self.rect.x
        self.bar.y = self.rect.y - 10


class Background(GameSprite):
    """游戏背景精灵"""

    def __init__(self, is_alt=False):
        """创建滚动背景，第二张背景可放在屏幕上方。"""

        # 1. 调用父类方法实现精灵的创建(image/rect/speed)
        super().__init__("./images/background.png")

        # 2. 判断是否是交替图像，如果是，需要设置初始位置
        if is_alt:
            self.rect.y = -self.rect.height

    def update(self):
        """滚动背景并在离屏后回到上方。"""

        # 1. 调用父类的方法实现
        super().update()

        # 2. 判断是否移出屏幕，如果移出屏幕，将图像设置到屏幕的上方
        if self.rect.y >= SCREEN_RECT.height:
            self.rect.y = -self.rect.height



class Boss(GameSprite):

    def __init__(self, difficulty="lunatic"):
        """初始化 Boss 阶段、血条、音效和弹幕难度参数。"""
        super().__init__("./images/enemy3_n1.png", 0, 1)
        self.music_boom = pygame.mixer.Sound("./music/enemy3_down.wav")
        self.music_fly = pygame.mixer.Sound("./music/enemy3_flying.wav")
        self.music_fly.play(-1)
        self.rect.centerx = 240
        self.y = 200
        self.isboom = False
        self.number = 3
        self.index1 = 1  # 控制动画速度
        self.index2 = 0
        self.index3 = 0
        self.index4 = 0
        self.injury = 1
        self.bar = bloodline(color_purple, 0, 0, 480, 8, BOSS_PHASE_HP[0])
        self.bullets = pygame.sprite.Group()
        self.danmaku_mode = "boss"
        self.danmaku_params = {}
        self.danmaku_timer = 0
        self.danmaku_interval = 30
        self.spiral_angle = 0
        self.phase = 0
        self.phase_timer = 0
        self.phase_duration = 300
        self.phase_colors = (color_blue, color_green, color_purple, (255, 150, 60), color_red)
        self.phase_state = "active"
        self.transition_timer = 0
        self.clear_complete = False
        self.difficulty = difficulty if difficulty in BOSS_INTERVAL_SCALE else "lunatic"
        self.interval_scale = BOSS_INTERVAL_SCALE[self.difficulty]
        self.fullscreen_interval_scale = BOSS_FULLSCREEN_INTERVAL_SCALE[self.difficulty]
        self.stage_notice = None

    def set_danmaku_mode(self, mode, **params):
        """保留通用弹幕模式接口，便于和普通敌机一致调用。"""
        self.danmaku_mode = mode
        self.danmaku_params = params

    def switch_phase(self, new_phase):
        """进入新阶段并触发补血、字幕和清弹提示。"""
        self.phase = new_phase
        self.phase_timer = 0
        self.transition_timer = 0
        self.phase_state = "filling"
        self.__set_phase_hp(new_phase)
        self.bar.length = 0
        self.stage_notice = new_phase + 1

    def __set_phase_hp(self, phase):
        """根据当前阶段刷新独立血量和血条权重。"""
        self.bar.value = float(BOSS_PHASE_HP[phase])
        self.bar.weight = 480 / self.bar.value

    def can_take_damage(self):
        """仅在阶段正式激活时允许受伤"""
        return self.phase_state == "active"

    def take_damage(self, damage):
        """扣除 Boss 血量，阶段血条归零后进入转阶段。"""
        if not self.can_take_damage():
            return False

        self.bar.length -= damage * self.bar.weight
        if self.bar.length <= 0.001:
            self.bar.length = 0
            self.__start_phase_break()
        return True

    def __start_phase_break(self):
        """启动阶段击破或最终击破流程。"""
        if self.phase_state != "active":
            return

        self.transition_timer = 0
        self.music_boom.play()
        if self.phase >= BOSS_PHASE_COUNT - 1:
            self.phase_state = "defeating"
            self.music_fly.stop()
        else:
            self.phase_state = "breaking"

    def __scaled_interval(self, value):
        """按当前难度缩放普通弹幕触发间隔。"""
        return max(1, int(round(value * self.interval_scale)))

    def __on_pattern(self, interval, offset=0):
        """判断普通弹幕本帧是否触发。"""
        interval = self.__scaled_interval(interval)
        return self.phase_timer % interval == min(offset, interval - 1)

    def __on_fullscreen_pattern(self, interval, offset=0):
        """判断全屏压制型弹幕本帧是否触发，normal 额外降频。"""
        interval = max(1, int(round(interval * self.interval_scale * self.fullscreen_interval_scale)))
        return self.phase_timer % interval == min(offset, interval - 1)

    def __fullscreen_group_active(self, round_interval, group_index, group_count, rounds_per_group=3):
        """让全屏弹幕按若干轮为一组交替启用。"""
        interval = max(1, int(round(round_interval * self.interval_scale * self.fullscreen_interval_scale)))
        round_index = self.phase_timer // interval
        return (round_index // rounds_per_group) % group_count == group_index

    def fire_danmaku(self, target_x=None, target_y=None):
        """按 Boss 当前阶段生成对应弹幕组合。"""
        if self.phase_state != "active":
            return []

        center_x = self.rect.centerx
        center_y = self.rect.bottom
        target_x = SCREEN_RECT.centerx if target_x is None else target_x
        target_y = SCREEN_RECT.bottom if target_y is None else target_y

        time = self.phase_timer
        self.spiral_angle += 0.045 + self.phase * 0.009

        #BOSS1-5阶段的不同弹幕调用
        if self.phase == 0:
            bullets = DanmakuPattern.ordered_aimed_ring(center_x, center_y, target_x, target_y, time,
                                                        24, 68, self.__scaled_interval(3),
                                                        2.7, "cyan", self.spiral_angle * 0.4)
            if self.__on_pattern(8):
                bullets.extend(DanmakuPattern.rotating_multi_directional(center_x, center_y, time,
                                                                         5, 2, 0.018, 2.15, "cyan", 8))
            if self.__on_pattern(78, 18):
                bullets.extend(DanmakuPattern.breathing_cluster(center_x, center_y - 10, time,
                                                                28, 54, 0.025, 24, "pink", 18, 1.35))
            if self.__on_pattern(52):
                bullets.extend(DanmakuPattern.double_circle(center_x, center_y, 12,
                                                            1.9, "blue", "cyan", self.spiral_angle))
            return bullets
        elif self.phase == 1:
            bullets = []
            if self.__on_pattern(28):
                bullets.extend(DanmakuPattern.gear_array(center_x, center_y, time,
                                                         12, 18, 36, 74, 1.85, "blue", "cyan"))
            if self.__on_pattern(36, 12):
                bullets.extend(DanmakuPattern.domino_wave(center_x, center_y, time, 7, 11, 28, 2.0))
            if self.__on_pattern(12):
                bullets.extend(DanmakuPattern.butterfly(center_x, center_y, 20,
                                                        2.0, "purple", self.spiral_angle))
            if self.__on_pattern(68, 20):
                bullets.extend(DanmakuPattern.fan(center_x, center_y, 9, 88, 2.6, "cyan",
                                                  math.atan2(target_y - center_y, target_x - center_x)))
            if self.__on_pattern(95, 28):
                laser_angle = math.atan2(target_y - center_y, target_x - center_x)
                bullets.append(LaserBeam(center_x, center_y, 38, SCREEN_RECT.height,
                                         38, 58, "purple", laser_angle))
            return bullets
        elif self.phase == 2:
            bullets = []
            if self.__on_pattern(10):
                bullets.extend(DanmakuPattern.spiral_petal(center_x, center_y, time,
                                                           5, 10, 98, 0.016, 1.85, "purple"))
            if self.__on_pattern(20, 1):
                bullets.extend(DanmakuPattern.dna_helix(center_x, center_y, time,
                                                        120, 48, 16, 2, 1.6, "cyan", "blue"))
            if self.__on_pattern(50):
                bullets.extend(DanmakuPattern.kaleidoscope_mirror(center_x, center_y, time,
                                                                  6, 3, 72, 2.35))
            if self.__on_pattern(80, 22):
                bullets.extend(DanmakuPattern.chrysanthemum(center_x, center_y, 10,
                                                            3, 1.55,
                                                            ("red", "orange", "yellow"), self.spiral_angle))
            if self.__on_pattern(60):
                bullets.extend(DanmakuPattern.sine_wave_wall(center_x, center_y, time,
                                                             16, 34, 2.05, "green"))
            return bullets
        elif self.phase == 3:
            bullets = []
            if self.__fullscreen_group_active(16, 0, 3, 3) and self.__on_fullscreen_pattern(12):
                bullets.extend(DanmakuPattern.rotating_stargate(center_x, center_y, time,
                                                                4, 20, 30, 24,
                                                                (0.034, -0.025, 0.018, -0.012),
                                                                ("red", "orange", "yellow", "white"), 1.9))
            if self.__fullscreen_group_active(16, 1, 3, 3) and self.__on_fullscreen_pattern(8, 2):
                bullets.extend(DanmakuPattern.shrinking_trap_ring(center_x, center_y, time,
                                                                  36, 168, 30, 0.019, "orange", 170))
            if self.__fullscreen_group_active(16, 2, 3, 3) and self.__on_fullscreen_pattern(6):
                bullets.extend(DanmakuPattern.hexagram_array(center_x, center_y, time, 90, 2.35))
            if self.__on_pattern(33, 18):
                bullets.extend(DanmakuPattern.star(center_x, center_y, 20,
                                                   2.35, "yellow", -self.spiral_angle))
            if self.__on_fullscreen_pattern(60, 18):
                for x in (-120, 40, 200, 360):
                    bullets.append(LaserBeam(x, -40, 26, SCREEN_RECT.height * 1.45,
                                             34, 54, "red", math.radians(58)))
                for x in (120, 280, 440, 600):
                    bullets.append(LaserBeam(x, -40, 26, SCREEN_RECT.height * 1.45,
                                             34, 54, "purple", math.radians(122)))
            return bullets
        else:
            bullets = DanmakuPattern.ordered_aimed_ring(center_x, center_y, target_x, target_y, time,
                                                        32, 86, self.__scaled_interval(2),
                                                        3.2, "pink", -self.spiral_angle)
            if self.__fullscreen_group_active(24, 0, 2, 3) and self.__on_fullscreen_pattern(4):
                bullets.extend(DanmakuPattern.waterwheel(center_x, center_y, time,
                                                         10, 6, 64, 0.044, 2, "cyan"))
            if self.__on_pattern(7, 2):
                bullets.extend(DanmakuPattern.petal_unfolding(center_x - 58, center_y - 16, time,
                                                              8, 6, 88, 0.008, "pink"))
                bullets.extend(DanmakuPattern.petal_unfolding(center_x + 58, center_y - 16, time,
                                                              8, 6, 88, -0.008, "pink"))
            if self.__fullscreen_group_active(24, 1, 2, 3) and self.__on_fullscreen_pattern(16):
                bullets.extend(DanmakuPattern.rotating_multi_directional(center_x, center_y, time,
                                                                         8, 2, 0.035, 2.6, "white", 10))
            if self.__on_pattern(38):
                bullets.extend(DanmakuPattern.yin_yang(center_x, center_y, 20,
                                                       2.25, self.spiral_angle))
            if self.__on_fullscreen_pattern(90, 20):
                laser_x = max(40, min(SCREEN_RECT.width - 40, target_x))
                bullets.append(LaserBeam(laser_x, 0, 64, SCREEN_RECT.height, 40, 80, "red"))
                bullets.append(LaserBeam(center_x - 115, 0, 40, SCREEN_RECT.height, 48, 65, "purple"))
                bullets.append(LaserBeam(center_x + 115, 0, 40, SCREEN_RECT.height, 48, 65, "purple"))
            return bullets

    def fire(self, target_x=None, target_y=None):
        """主循环调用的 Boss 发射入口。"""
        return self.fire_danmaku(target_x, target_y)

    def draw_phase_bar(self, canvas):
        """绘制当前阶段环形血条。"""
        max_length = self.bar.weight * self.bar.value
        ratio = max(0, min(1, self.bar.length / max_length))
        radius = max(self.rect.width, self.rect.height) // 2 + 14
        arc_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        arc_rect.center = self.rect.center

        start_angle = math.radians(-90)
        end_angle = start_angle + math.pi * 2
        pygame.draw.arc(canvas, (70, 70, 80), arc_rect, start_angle, end_angle, 5)
        if ratio > 0:
            pygame.draw.arc(canvas, self.phase_colors[self.phase], arc_rect,
                            start_angle, start_angle + math.pi * 2 * ratio, 7)

    def update(self):
        """更新 Boss 移动、动画、转阶段和死亡流程。"""
        # 左右移
        global SCORE
        if self.phase_state != "defeating" and self.index4 % 2 == 0:  # 降低帧速率,注意这两个指针不能一样
            # 内部为左右移动大概50像素
            if self.index3 % 50 == 0 and (self.index3 // 50) % 2 == 1:
                self.speedx = -self.speedx
            self.rect.x += self.speedx
            self.index3 += 1
        self.index4 += 1

        # 发电动画
        self.image = pygame.image.load("./images/enemy3_n" + str((self.index1 // 6) % 2 + 1) + ".png")
        self.index1 += 1

        if self.phase_state == "breaking":
            self.transition_timer += 1
            if self.transition_timer % 10 < 5:
                flash_image = self.image.copy()
                flash_image.fill((180, 180, 180), special_flags=pygame.BLEND_RGB_ADD)
                self.image = flash_image
            if self.transition_timer >= BOSS_PHASE_BREAK_FRAMES:
                self.switch_phase(self.phase + 1)
        elif self.phase_state == "filling":
            self.transition_timer += 1
            max_length = self.bar.weight * self.bar.value
            self.bar.length = max_length * min(1, self.transition_timer / BOSS_PHASE_FILL_FRAMES)
            if self.transition_timer >= BOSS_PHASE_FILL_FRAMES:
                self.bar.length = max_length
                self.phase_state = "active"
                self.phase_timer = 0
        elif self.phase_state == "defeating":
            if self.index2 < 29:  # 4*7+1
                self.image = pygame.image.load("./images/enemy3_down" + str(self.index2 // 7) + ".png")
                self.index2 += 1
            else:
                self.clear_complete = True
                self.kill()
                SCORE += self.bar.value
        else:
            self.phase_timer += 1


class Enemy(GameSprite):
    """敌机精灵"""

    def __init__(self, num=1):
        """按类型创建普通敌机并配置血量、速度和弹幕模式。"""
        self.number = num
        # 1. 调用父类方法，创建敌机精灵，同时指定敌机图片
        super().__init__("./images/enemy" + str(num) + ".png")

        # music
        if num == 1:
            self.music_boom = pygame.mixer.Sound("./music/enemy1_down.wav")
        else:
            self.music_boom = pygame.mixer.Sound("./music/enemy2_down.wav")
        # 2. 指定敌机的初始随机速度 1 ~ 3
        self.speedy = random.randint(1, 3)

        # 3. 指定敌机的初始随机位置
        self.rect.bottom = 0
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)

        # 4.爆炸效果
        self.isboom = False
        self.index = 0

        # 5.血条
        if self.number == 1:
            self.bar = bloodline(color_blue, self.rect.x, self.rect.y, self.rect.width, 3, 4)
        else:
            self.bar = bloodline(color_blue, self.rect.x, self.rect.y, self.rect.width, 4, 12)

        # 6,子弹
        self.bullets = pygame.sprite.Group()
        self.danmaku_mode = None
        self.danmaku_params = {}
        self.danmaku_timer = 0
        self.danmaku_interval = 30
        self.spiral_angle = 0

        if self.number == 1:
            self.set_danmaku_mode(random.choice(("aimed", "fan")),
                                  color=random.choice(("blue", "cyan", "yellow")))
        else:
            self.set_danmaku_mode(random.choice(("fan", "aimed", "circle", "spiral", "mixed")),
                                  color=random.choice(("red", "blue", "cyan", "yellow", "purple")))

    def set_danmaku_mode(self, mode, **params):
        """设置普通敌机当前弹幕模式和颜色参数。"""
        self.danmaku_mode = mode
        self.danmaku_params = params

    def fire_danmaku(self, target_x=None, target_y=None):
        """根据普通敌机模式生成弹幕。"""
        center_x = self.rect.centerx
        center_y = self.rect.bottom
        color = self.danmaku_params.get("color", "red")
        target_x = SCREEN_RECT.centerx if target_x is None else target_x
        target_y = SCREEN_RECT.bottom if target_y is None else target_y

        if self.danmaku_mode == "circle":
            self.spiral_angle += 0.16
            bullet_count = 8 if self.number == 1 else 14
            speed = 1.8 if self.number == 1 else 2.2
            return DanmakuPattern.circle(center_x, center_y, bullet_count, 10, speed, color, self.spiral_angle)
        elif self.danmaku_mode == "fan":
            direction = math.atan2(target_y - center_y, target_x - center_x)
            bullet_count = 3 if self.number == 1 else 9
            angle_span = 45 if self.number == 1 else 90
            speed = 2.0 if self.number == 1 else 2.5
            return DanmakuPattern.fan(center_x, center_y, bullet_count, angle_span, speed, color, direction)
        elif self.danmaku_mode == "aimed":
            bullet_count = 1 if self.number == 1 else 5
            speed = 2.2 if self.number == 1 else 2.7
            return DanmakuPattern.aimed(center_x, center_y, bullet_count, speed, color, target_x, target_y)
        elif self.danmaku_mode == "spiral":
            bullets = DanmakuPattern.spiral(center_x, center_y, 4, 2.4, color, 0.07, self.spiral_angle)
            self.spiral_angle += 0.07
            return bullets
        elif self.danmaku_mode == "mixed":
            direction = math.atan2(target_y - center_y, target_x - center_x)
            bullets = DanmakuPattern.fan(center_x, center_y, 6, 75, 2.4, color, direction)
            bullets.extend(DanmakuPattern.aimed(center_x, center_y, 3, 2.7, "purple", target_x, target_y))
            return bullets
        return []

    def fire(self, target_x=None, target_y=None):
        """普通敌机发射入口，优先使用弹幕模式。"""
        if self.danmaku_mode:
            return self.fire_danmaku(target_x, target_y)

        fired_bullets = []
        for i in range(0, 2):
            # 1. 创建子弹精灵
            bullet = Bullet(0, random.randint(self.speedy + 1, self.speedy + 3))
            # 2. 设置精灵的位置
            bullet.rect.bottom = self.rect.bottom + i * 20
            bullet.rect.centerx = self.rect.centerx

            # 3. 将精灵添加到精灵组
            self.bullets.add(bullet)
            fired_bullets.append(bullet)
        return fired_bullets

    def update(self):
        """更新敌机移动、离屏销毁和爆炸动画。"""
        global SCORE
        # 1. 调用父类方法，保持垂直方向的飞行
        super().update()

        # 2. 判断是否飞出屏幕，如果是，需要从精灵组删除敌机
        if self.rect.y > SCREEN_RECT.height:
            # print("飞出屏幕，需要从精灵组删除...")
            # kill方法可以将精灵从所有精灵组中移出，精灵就会被自动销毁
            self.kill()
            self.bar.length = 0

        if self.isboom:
            self.bar.length -= self.bar.weight * self.injury
            if self.bar.length <= 0:
                if self.index == 0:  # 保证只响一次
                    self.music_boom.play()
                if self.index < 17:  # 4*4+1
                    self.image = pygame.image.load(
                        "./images/enemy" + str(self.number) + "_down" + str(self.index // 4) + ".png")
                    # 这个地方之所以要整除4是为了减慢爆炸的速度，如果按照update的频率60hz就太快了
                    self.index += 1
                else:
                    self.kill()
                    SCORE += self.bar.value


            else:
                self.isboom = False


class Hero(GameSprite):
    """英雄精灵"""

    def __init__(self, max_hp=10):
        """初始化英雄尺寸、生命、弹幕等级和受伤反馈状态。"""
        # 1. 调用父类方法，设置image&speed
        super().__init__("./images/me1.png")
        self.music_down = pygame.mixer.Sound("./music/me_down.wav")
        self.music_upgrade = pygame.mixer.Sound("./music/upgrade.wav")
        self.music_degrade = pygame.mixer.Sound("./music/supply.wav")

        self.number = 0
        # 2. 设置英雄的初始位置
        self.hero_scale = HERO_SCALE
        self.__set_hero_image("./images/me1.png")
        self.rect.centerx = SCREEN_RECT.centerx
        self.rect.bottom = SCREEN_RECT.bottom - 120

        # 3. 创建子弹的精灵组
        self.bullets = pygame.sprite.Group()
        # 4.爆炸
        self.isboom = False
        self.index1 = 1  # 控制动画速度
        self.index2 = 0
        # 5.buff1加成
        self.buff1_num = 0
        # 6,英雄血条
        self.bar = bloodline(color_green, 0, 700, 480, 8, max_hp)
        # 7，炸弹数目
        self.bomb = 0
        # 8，受伤闪白反馈
        self.hit_flash_end = 0
        # 9，弹幕环境下的容错判定
        self.invincible_frames = 0
        self.hitbox_scale = HERO_HITBOX_SCALE
        self.focus_hitbox_size = HERO_FOCUS_HITBOX_SIZE
        self.focus_mode = False

    def flash_hit(self):
        """启动英雄受击白色闪烁。"""
        self.hit_flash_end = pygame.time.get_ticks() + HERO_HIT_FLASH_MS

    def bullet_level(self):
        """返回当前子弹等级。"""
        return min(self.buff1_num + 1, MAX_BULLET_LEVEL)

    def bullet_damage(self):
        """返回当前等级的单发子弹伤害。"""
        return BULLET_LEVEL_DAMAGE[self.bullet_level() - 1]

    def add_bullet(self, bullet):
        """设置英雄子弹伤害并加入子弹组。"""
        bullet.hity = self.bullet_damage()
        self.bullets.add(bullet)

    def __set_hero_image(self, image_name):
        """按缩放比例替换英雄当前图片并保持中心点。"""
        center = self.rect.center
        image = pygame.image.load(image_name)
        size = (max(1, int(image.get_width() * self.hero_scale)),
                max(1, int(image.get_height() * self.hero_scale)))
        self.image = pygame.transform.smoothscale(image, size)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        """更新英雄移动边界、动画、无敌帧和低速判定点。"""

        # 英雄在水平方向移动和血条不同步,特殊
        self.rect.y += self.speedy
        self.rect.x += self.speedx

        # 控制英雄不能离开屏幕
        if self.rect.x < 0:
            self.rect.x = 0
        elif self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right
        elif self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_RECT.bottom:
            self.rect.bottom = SCREEN_RECT.bottom

        # 英雄喷气动画

        self.__set_hero_image("./images/me" + str((self.index1 // 6) % 2 + 1) + ".png")
        self.index1 += 1
        if self.invincible_frames > 0:
            self.invincible_frames -= 1

        # 英雄爆炸动画
        if self.isboom:
            self.bar.length -= self.injury * self.bar.weight
            if self.bar.length <= 0:  # 此时满足爆炸的条件了
                if self.index2 == 0:
                    self.music_down.play()
                if self.index2 < 17:  # 4*4+1
                    self.__set_hero_image("./images/me_destroy_" + str(self.index2 // 4) + ".png")
                    # 这个地方之所以要整除4是为了减慢爆炸的速度，如果按照update的频率60hz就太快了
                    self.index2 += 1
                else:
                    self.kill()
                return
            else:
                self.isboom = False  # 否则还不能死

        if pygame.time.get_ticks() < self.hit_flash_end:
            flash_image = self.image.copy()
            flash_image.fill((180, 180, 180), special_flags=pygame.BLEND_RGB_ADD)
            self.image = flash_image

        if self.invincible_frames > 0 and self.invincible_frames % 6 < 3:
            invincible_image = self.image.copy()
            invincible_image.set_alpha(100)
            self.image = invincible_image

        if self.focus_mode:
            center = (self.image.get_width() // 2, self.image.get_height() // 2)
            pygame.draw.circle(self.image, (20, 20, 20), center, 4)
            pygame.draw.circle(self.image, (255, 255, 255), center, 3)

    # 发射子弹
    def fire(self):
        """根据当前等级生成英雄子弹。"""
        if self.buff1_num == 0:
            for i in range(0, 1):
                # 1. 创建子弹精灵
                bullet = Bullet()

                # 2. 设置精灵的位置
                bullet.rect.bottom = self.rect.y - i * 20
                bullet.rect.centerx = self.rect.centerx

                # 3. 将精灵添加到精灵组
                self.add_bullet(bullet)
        elif self.buff1_num <= 3:
            for i in (0, 1):
                # 1. 创建子弹精灵
                for j in range(2, self.buff1_num + 3):
                    bullet = Bullet(2, HERO_BULLET_SPEED)
                    # 2. 设置精灵的位置
                    bullet.rect.bottom = self.rect.y - i * 20
                    if (self.buff1_num % 2 == 1):
                        bullet.rect.centerx = self.rect.centerx + (-1) ** j * 15 * (j // 2)
                    if (self.buff1_num % 2 == 0):
                        if j == 2:
                            bullet.rect.centerx = self.rect.centerx
                        else:
                            bullet.rect.centerx = self.rect.centerx + (-1) ** j * 15 * ((j - 1) // 2)
                    # 3. 将精灵添加到精灵组
                    self.add_bullet(bullet)
        elif self.buff1_num >= 4:
            for i in range(0, 1):
                # 1. 表示有几层
                for j in range(2, 5):  # 每层三个

                    bullet = Bullet(3, HERO_BULLET_SPEED)
                    bullet.injury = 2
                    # 2. 设置精灵的位置
                    bullet.rect.bottom = self.rect.y
                    if j == 2:
                        bullet.rect.centerx = self.rect.centerx
                    else:
                        bullet.rect.centerx = self.rect.centerx + (-1) ** j * (30 + 5 * i)
                        bullet.speedx = (-1) ** j * (i + 1)
                    self.add_bullet(bullet)


class Heromate(Hero):
    def __init__(self, num):
        """创建跟随英雄左右两侧的僚机。"""
        super().__init__()
        self.image = pygame.image.load("./images/life.png")
        self.number = num

    def update(self):
        """限制僚机不越出屏幕边界。"""

        if self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_RECT.bottom:
            self.rect.bottom = SCREEN_RECT.bottom

    def fire(self):
        """僚机发射单发直线子弹。"""
        for i in range(0, 1, 2):
            # 1. 创建子弹精灵
            bullet = Bullet()
            # 2. 设置精灵的位置
            bullet.rect.bottom = self.rect.y - i * 20
            bullet.rect.centerx = self.rect.centerx
            # 3. 将精灵添加到精灵组
            self.bullets.add(bullet)


class Bullet(GameSprite):
    """子弹精灵"""

    def __init__(self, color=1, speedy=HERO_BULLET_SPEED, speedx=0):
        """创建英雄或旧敌机使用的直线子弹。"""
        # 调用父类方法，设置子弹图片，设置初始速度
        self.hity = color  # 子弹伤害值
        self.music_shoot = pygame.mixer.Sound("./music/bullet.wav")
        self.music_shoot.set_volume(0.4)
        if color > 0:  # 只让英雄发子弹响
            self.music_shoot.play()
        super().__init__("./images/bullet" + str(color) + ".png", speedy, speedx)

    def update(self):
        """移动子弹并在离屏后销毁。"""
        # 调用父类方法，让子弹沿垂直方向飞行
        super().update()

        # 判断子弹是否飞出屏幕
        if self.rect.bottom < 0 or self.rect.y > 700:
            self.kill()


class Buff1(GameSprite):
    def __init__(self):
        """创建子弹升级补给。"""
        super().__init__("./images/bullet_supply.png", 1)
        self.music_get = pygame.mixer.Sound("./music/get_bullet.wav")
        self.rect.bottom = 0
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)

    def update(self):
        """更新升级补给下落并在离屏后销毁。"""
        super().update()
        if self.rect.bottom < 0:
            self.kill()


class Buff2(GameSprite):
    def __init__(self):
        """创建旧炸弹补给的基础对象。"""
        super().__init__("./images/bomb_supply.png", 2)
        self.music_get = pygame.mixer.Sound("./music/get_bomb.wav")
        self.rect.bottom = random.randint(0, 700)
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)
        self.ran = random.randint(60, 180)  # 在持续1~3s后消失

    def update(self):
        """更新补给移动和超时销毁。"""
        super().update()
        if self.rect.bottom < 0 or self.index == self.ran:
            self.kill()
        self.index += 1

class Buff3(Buff2):
    def __init__(self):
        """创建回血补给。"""
        super().__init__()
        self.image = pygame.image.load("./images/buff3.png")
        self.speedy=3


class bloodline(object):
    def __init__(self, color, x, y, length, width=2, value=2):
        """初始化线形血条的颜色、长度和最大值。"""
        self.color = color
        self.x = x
        self.y = y
        self.length = length
        self.width = width  # 线宽
        self.value = value * 1.0  # 血量用浮点数
        self.weight = length / value  # 每一滴血表示的距离
        self.color_init = color

    def update(self, canvas):
        """按当前血量绘制血条，低血量时变红。"""
        if self.length <= self.value * self.weight / 2:
            self.color = color_red
        else:
            self.color = self.color_init
        self.bar_rect = pygame.draw.line(canvas, self.color, (self.x, self.y), (self.x + self.length, self.y),
                                         self.width)


class CanvasOver():
    def __init__(self, screen):
        """初始化失败界面的按钮和背景贴图。"""
        self.img_again = pygame.image.load("./images/again.png")
        self.img_over = pygame.image.load("./images/gameover.png")
        self.rect_again = self.img_again.get_rect()
        self.rect_over = self.img_over.get_rect()
        self.rect_again.centerx = self.rect_over.centerx = SCREEN_RECT.centerx
        self.rect_again.bottom = SCREEN_RECT.centery
        self.rect_over.y = self.rect_again.bottom + 20
        self.screen = screen

    def event_handler(self, event):
        """处理失败/通关界面的重新开始或退出点击。"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.rect_again.left < pos[0] < self.rect_again.right and \
                    self.rect_again.top < pos[1] < self.rect_again.bottom:
                return 1
            elif self.rect_over.left < pos[0] < self.rect_over.right and \
                    self.rect_over.top < pos[1] < self.rect_over.bottom:
                return 0

    def update(self):
        """绘制失败界面和分数。"""
        self.screen.blit(self.img_again, self.rect_again)
        self.screen.blit(self.img_over, self.rect_over)
        score_font = pygame.font.Font("./STCAIYUN.ttf", 50)
        image = score_font.render("SCORE:" + str(int(SCORE)), True, color_gray)
        rect = image.get_rect()
        rect.centerx, rect.bottom = SCREEN_RECT.centerx, self.rect_again.top - 20
        self.screen.blit(image, rect)


class CanvasClear(CanvasOver):
    def update(self):
        """绘制通关界面、复用按钮并显示分数。"""
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.img_again, self.rect_again)
        self.screen.blit(self.img_over, self.rect_over)

        title_font = pygame.font.Font("./STCAIYUN.ttf", 48)
        title = title_font.render("CONGRATULATIONS!", True, color_gray)
        title_rect = title.get_rect()
        title_rect.centerx, title_rect.bottom = SCREEN_RECT.centerx, self.rect_again.top - 30
        self.screen.blit(title, title_rect)

        score_font = pygame.font.Font("./STCAIYUN.ttf", 34)
        image = score_font.render("SCORE:" + str(int(SCORE)), True, color_gray)
        rect = image.get_rect()
        rect.centerx, rect.top = SCREEN_RECT.centerx, self.rect_over.bottom + 20
        self.screen.blit(image, rect)
