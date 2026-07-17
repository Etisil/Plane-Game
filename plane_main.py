import sys
import pygame

pygame.init()
from plane_sprites import *

MAX_DANMAKU_BULLETS = 650
DANMAKU_REMOVE_RATE = 0.1
BOSS_WARNING_DURATION_MS = 2400


class PlaneGame(object):
    """飞机大战主游戏"""

    def __init__(self, difficulty="lunatic"):
        """初始化窗口、精灵组、音效、UI 状态和定时器。"""
        print("游戏初始化")
        reset_score()
        self.difficulty = difficulty if difficulty in DIFFICULTY_HERO_HP else "lunatic"

        # 1. 创建游戏的窗口
        self.screen = pygame.display.set_mode(SCREEN_RECT.size)
        pygame.display.set_caption("弹幕飞机大战")
        # 创建结束界面
        self.canvas_over = CanvasOver(self.screen)
        self.canvas_clear = CanvasClear(self.screen)
        # 2. 创建游戏的时钟
        self.clock = pygame.time.Clock()
        # 3. 调用私有方法，精灵和精灵组的创建
        self.__create_sprites()
        # 分数对象
        self.score = GameScore()
        # 程序控制指针
        self.index = 0
        # 音乐bgm
        self.bg_music = pygame.mixer.Sound("./music/game_music.ogg")
        self.bg_music.set_volume(0.3)
        self.bg_music.play(-1)
        # 游戏结束了吗
        self.game_over = False
        self.game_clear = False
        self.boss_mode = False
        self.paused = False
        self.pause_snapshot = None
        self.pause_font = pygame.font.Font(None, 80)
        self.buff_font = pygame.font.Font(None, 30)
        self.warning_font = pygame.font.Font(None, 96)
        self.stage_font = pygame.font.Font(None, 74)
        self.boss_warning = False
        self.boss_warning_end = 0
        self.damage_flash_end = 0
        self.stage_notice_text = None
        self.stage_notice_start = 0
        self.stage_notice_duration = 900
        self.phase_wave_start = 0
        self.phase_wave_duration = 520
        # 4. 设置定时器事件 - 创建敌机
        pygame.time.set_timer(CREATE_ENEMY_EVENT, 1800)
        pygame.time.set_timer(HERO_FIRE_EVENT, 160)
        pygame.time.set_timer(BUFF1_SHOW_UP, random.randint(10000, 20000))
        pygame.time.set_timer(BUFF2_SHOW_UP, random.randint(20000, 40000))
        pygame.time.set_timer(ENEMY_FIRE_EVENT, 1400)

    def __create_sprites(self):
        """创建背景、英雄、敌机、弹幕、Buff 等精灵组。"""

        # 创建背景精灵和精灵组
        bg1 = Background()
        bg2 = Background(True)

        self.back_group = pygame.sprite.Group(bg1, bg2)

        # 创建敌机的精灵组

        self.enemy_group = pygame.sprite.Group()

        # 创建英雄的精灵和精灵组
        self.hero = Hero(DIFFICULTY_HERO_HP[self.difficulty])
        self.hero_group = pygame.sprite.Group(self.hero)

        # 创建敌军子弹组
        self.enemy_bullet_group = pygame.sprite.Group()
        self.danmaku_group = pygame.sprite.Group()

        # 血条列表
        self.bars = []
        self.bars.append(self.hero.bar)

        # 创建buff组
        self.buff1_group = pygame.sprite.Group()

        # 创建假象boom组
        self.enemy_boom = pygame.sprite.Group()

    def start_game(self):
        """运行主循环，按当前状态进入游戏、暂停、失败或通关界面。"""
        print("游戏开始...")

        while True:
            # 1. 设置刷新帧率
            self.clock.tick(FRAME_PER_SEC)
            # 2. 事件监听
            self.__event_handler()

            # 是否要结束游戏

            if self.game_clear:
                self.canvas_clear.update()
            elif self.game_over:
                self.canvas_over.update()
            elif self.paused:
                self.__show_paused()
            else:
                # 3. 碰撞检测
                self.__check_collide()
                # 4. 更新/绘制精灵组
                self.__update_sprites()

            # 5. 更新显示
            pygame.display.update()

    def __event_handler(self):  # 事件检测
        """处理键盘、鼠标和定时器事件。"""

        self.__update_boss_warning()

        for event in pygame.event.get():
            # 判断是否退出游戏
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_p and not self.game_over and not self.game_clear:
                self.__toggle_pause()
                continue

            if self.game_over == True or self.game_clear == True:
                canvas = self.canvas_clear if self.game_clear else self.canvas_over
                flag = canvas.event_handler(event)
                if flag == 1:
                    self.__start__()
                elif flag == 0:
                    pygame.quit()
                    sys.exit()
                continue

            if self.paused:
                continue

            if event.type == CREATE_ENEMY_EVENT:
                if self.boss_mode:
                    continue

                # 创建敌机精灵将敌机精灵添加到敌机精灵组
                score = self.score.getvalue()
                enemy_count = 1

                #精英敌机创建条件、概率
                for _ in range(enemy_count):
                    if score < 50:
                        enemy = Enemy()
                    else:
                        enemy = Enemy(2 if random.randint(0, 100) < 45 else 1)

                    self.enemy_group.add(enemy)
                    self.bars.append(enemy.bar)

            elif event.type == HERO_FIRE_EVENT:
                for hero in self.hero_group:
                    hero.fire()
            elif event.type == BUFF1_SHOW_UP:
                buff1 = Buff1()
                self.buff1_group.add(buff1)
            elif event.type == BUFF2_SHOW_UP:
                if not self.boss_mode and self.hero.bar.color == color_red:#按需分配
                    buff = Buff3()
                    self.buff1_group.add(buff)
            elif event.type == ENEMY_FIRE_EVENT:
                for enemy in self.enemy_group:
                    if isinstance(enemy, Boss):
                        continue
                    if enemy.danmaku_mode:
                        bullets = enemy.fire(self.hero.rect.centerx, self.hero.rect.centery)
                        for bullet in bullets:
                            self.__add_enemy_projectile(bullet)

        # 使用键盘提供的方法获取键盘按键 - 按键元组
        if self.paused or self.game_over or self.game_clear:
            self.heros_move(0, 0)
            self.hero.focus_mode = False
            return

        keys_pressed = pygame.key.get_pressed()
        self.hero.focus_mode = keys_pressed[pygame.K_x]
        move_speed = 2 if self.hero.focus_mode else 5
        x = 0
        y = 0

        if keys_pressed[pygame.K_RIGHT] or keys_pressed[pygame.K_d]:
            x += move_speed
        if keys_pressed[pygame.K_LEFT] or keys_pressed[pygame.K_a]:
            x -= move_speed
        if keys_pressed[pygame.K_UP] or keys_pressed[pygame.K_w]:
            y -= move_speed
        if keys_pressed[pygame.K_DOWN] or keys_pressed[pygame.K_s]:
            y += move_speed

        if x and y:
            diagonal_speed = max(1, round(move_speed * 0.707))
            x = diagonal_speed if x > 0 else -diagonal_speed
            y = diagonal_speed if y > 0 else -diagonal_speed

        self.heros_move(x, y)

    def heros_move(self, x=0, y=0):
        """设置英雄当前帧移动速度。"""
        self.hero.speedx = x
        self.hero.speedy = y

    def __toggle_pause(self):
        """切换暂停状态并保存暂停画面。"""
        self.paused = not self.paused
        self.pause_snapshot = self.screen.copy() if self.paused else None
        self.heros_move(0, 0)

    def __show_paused(self):
        """绘制暂停遮罩和 PAUSED 文本。"""
        if self.pause_snapshot:
            self.screen.blit(self.pause_snapshot, (0, 0))

        overlay = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        image = self.pause_font.render("PAUSED", True, color_gray)
        rect = image.get_rect(center=SCREEN_RECT.center)
        self.screen.blit(image, rect)

    def __update_boss_warning(self):
        """检查分数阈值，触发 Boss 出现前的 WARNING 流程。"""
        if self.paused or self.game_over or self.game_clear:
            return

        now = pygame.time.get_ticks()
        if self.boss_warning:
            if now >= self.boss_warning_end:
                self.__spawn_boss()
            return

        if self.boss_mode:
            return

        if self.score.getvalue() > 120 + 420 * self.index:
            self.boss_mode = True
            self.__clear_for_boss()
            self.boss_warning = True
            self.boss_warning_end = now + BOSS_WARNING_DURATION_MS

    def __spawn_boss(self):
        """清场后创建 Boss 并进入 Boss 模式。"""
        self.boss_mode = True
        self.__clear_for_boss()
        self.boss = Boss(self.difficulty)
        self.enemy_group.add(self.boss)
        self.index += 1
        self.boss_warning = False

    def __clear_for_boss(self):
        """清理普通敌人、子弹、弹幕和 Buff。"""
        self.enemy_group.empty()
        self.enemy_boom.empty()
        self.enemy_bullet_group.empty()
        self.danmaku_group.empty()
        self.buff1_group.empty()
        self.bars = [self.hero.bar]

    def __finish_game_clear(self):
        """进入通关状态并清理战斗对象。"""
        self.game_clear = True
        self.boss_mode = False
        self.enemy_group.empty()
        self.enemy_boom.empty()
        self.enemy_bullet_group.empty()
        self.danmaku_group.empty()
        self.buff1_group.empty()

    def __show_warning(self):
        """绘制 Boss 出现前的 WARNING 闪烁提示。"""
        if not self.boss_warning:
            return

        now = pygame.time.get_ticks()
        alpha = 80 if (now // 350) % 2 else 150
        overlay = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
        overlay.fill((120, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

        image = self.warning_font.render("WARNING!", True, (255, 60, 60))
        rect = image.get_rect(center=SCREEN_RECT.center)
        self.screen.blit(image, rect)

    def __hero_bullet_hitbox(self):
        """返回英雄当前碰撞判定框，低速模式下使用中心白点。"""
        if self.hero.focus_mode:
            width = height = self.hero.focus_hitbox_size
        else:
            width = max(4, int(self.hero.rect.width * self.hero.hitbox_scale))
            height = max(4, int(self.hero.rect.height * self.hero.hitbox_scale))
        hitbox = pygame.Rect(0, 0, width, height)
        hitbox.center = self.hero.rect.center
        return hitbox

    def __hurt_hero_by_bullet(self, bullet):
        """处理英雄被敌弹击中后的扣血、闪烁和无敌帧。"""
        bullet.kill()
        self.hero.injury = 1

        self.hero.invincible_frames = 60
        self.__show_damage_flash()
        self.hero.flash_hit()
        self.hero.isboom = True

    def __show_damage_flash(self):
        """启动全屏红色受伤闪烁效果。"""
        self.damage_flash_end = pygame.time.get_ticks() + 180

    def __bullet_hits_hero(self, bullet, hero_hitbox):
        """兼容普通弹幕和激光的英雄碰撞检测。"""
        if hasattr(bullet, "collides_with"):
            return bullet.collides_with(hero_hitbox)
        return hero_hitbox.colliderect(bullet.rect)

    def __check_collide(self):
        """统一处理英雄、敌机、子弹和 Buff 的碰撞。"""

        # 1. 子弹摧毁敌机
        for enemy in self.enemy_group:
            for hero in self.hero_group:
                for bullet in hero.bullets:
                    if pygame.sprite.collide_mask(bullet, enemy):  # 这种碰撞检测可以精确到像素去掉alpha遮罩的那种哦
                        if isinstance(enemy, Boss):
                            if enemy.take_damage(bullet.hity):
                                bullet.kill()
                        else:
                            bullet.kill()
                            enemy.injury = bullet.hity
                            enemy.isboom = True
                            if enemy.bar.length <= 0:
                                self.enemy_group.remove(enemy)
                                self.enemy_boom.add(enemy)

        # 2. 敌机撞毁英雄
        for enemy in self.enemy_group:
            if self.__hero_bullet_hitbox().colliderect(enemy.rect):
                if enemy.number < 3:
                    enemy.bar.length = 0  # 敌机直接死
                    self.hero.injury = self.hero.bar.value / 4  # 英雄掉四分之一的血
                    self.enemy_group.remove(enemy)
                    self.enemy_boom.add(enemy)
                    enemy.isboom = True
                else:
                    self.hero.bar.length = 0
                self.__show_damage_flash()
                self.hero.flash_hit()
                self.hero.isboom = True

        # 敌弹击中英雄。弹幕子弹使用缩小判定框，给玩家留出躲避空间。
        if self.hero.invincible_frames <= 0:
            hero_hitbox = self.__hero_bullet_hitbox()
            for bullet in self.danmaku_group:
                if getattr(bullet, "harmful", True) and self.__bullet_hits_hero(bullet, hero_hitbox):
                    self.__hurt_hero_by_bullet(bullet)
                    break

        if self.hero.invincible_frames <= 0:
            hero_hitbox = self.__hero_bullet_hitbox()
            for bullet in self.enemy_bullet_group:
                if getattr(bullet, "harmful", True) and self.__bullet_hits_hero(bullet, hero_hitbox):
                    self.__hurt_hero_by_bullet(bullet)
                    break

        if not self.hero.alive():
            self.hero.rect.right = -10  # 把英雄移除屏幕
            self.game_over = True

        # 3.buff吸收
        for buff in self.buff1_group:
            if pygame.sprite.collide_mask(self.hero, buff):
                buff.music_get.play()
                if buff.speedy == 1:  # 用速度来区分
                    if self.hero.buff1_num < MAX_BULLET_LEVEL - 1:
                        self.hero.buff1_num += 1
                        self.hero.music_upgrade.play()

                elif buff.speedy==3:
                    if self.hero.bar.length < self.hero.bar.weight*self.hero.bar.value:
                        self.hero.bar.length += self.hero.bar.weight*self.hero.bar.value
                buff.kill()

    def team_show(self):
        """创建跟随英雄的僚机对象。"""
        self.mate1 = Heromate(-1)
        self.mate2 = Heromate(1)
        self.mate1.image = pygame.image.load("./images/life.png")
        self.mate1.rect = self.mate1.image.get_rect()
        self.mate2.image = pygame.image.load("./images/life.png")
        self.mate2.rect = self.mate2.image.get_rect()
        self.hero_group.add(self.mate1)
        self.hero_group.add(self.mate2)

    # 各种更新
    def __update_sprites(self):
        """按绘制顺序更新并渲染所有精灵和 UI。"""

        self.back_group.update()
        self.back_group.draw(self.screen)

        self.enemy_group.update()
        self.__consume_boss_stage_notice()
        self.__boss_auto_fire()
        self.enemy_group.draw(self.screen)
        self.__draw_boss_phase_bars()

        self.enemy_boom.update()
        self.enemy_boom.draw(self.screen)

        self.heros_update()
        self.hero_group.draw(self.screen)

        for hero in self.hero_group:
            hero.bullets.update()
            hero.bullets.draw(self.screen)

        self.buff1_group.update()
        self.buff1_group.draw(self.screen)

        self.bars_update()

        self.enemy_bullet_group.update()
        self.enemy_bullet_group.draw(self.screen)
        self.__limit_danmaku_bullets()
        self.danmaku_group.update()
        self.danmaku_group.draw(self.screen)

        self.score_show()
        self.buff_level_show()
        self.hp_show()
        self.__draw_damage_flash()
        self.__show_warning()
        self.__draw_phase_wave()
        self.__draw_stage_notice()
        self.__check_boss_clear()

    def heros_update(self):
        """更新英雄与僚机位置。"""
        for hero in self.hero_group:
            if hero.number == 1:
                hero.rect.bottom = self.hero.rect.bottom
                hero.rect.left = self.hero.rect.right
            if hero.number == -1:
                hero.rect.bottom = self.hero.rect.bottom
                hero.rect.right = self.hero.rect.left
            hero.update()

    def bars_update(self):
        """更新所有仍有长度的血条。"""
        for bar in self.bars:
            if bar.length > 0:
                bar.update(self.screen)
            else:
                self.bars.remove(bar)

    def bullet_enemy_update(self):
        """更新并绘制旧敌机子弹组。"""
        for enemy in self.enemy_group:
            enemy.bullets.update()
            enemy.bullets.draw(self.screen)

    def __add_enemy_projectile(self, bullet):
        """按类型把敌方投射物放入普通子弹组或弹幕组。"""
        if isinstance(bullet, (DanmakuBullet, LaserBeam)):
            self.danmaku_group.add(bullet)
        else:
            self.enemy_bullet_group.add(bullet)

    def __boss_auto_fire(self):
        """Boss 模式下每帧请求 Boss 生成弹幕。"""
        if not self.boss_mode or self.boss_warning:
            return

        for enemy in self.enemy_group:
            if isinstance(enemy, Boss):
                bullets = enemy.fire(self.hero.rect.centerx, self.hero.rect.centery)
                for bullet in bullets:
                    self.__add_enemy_projectile(bullet)

    def __draw_boss_phase_bars(self):
        """绘制所有 Boss 的阶段环形血条。"""
        for enemy in self.enemy_group:
            if isinstance(enemy, Boss):
                enemy.draw_phase_bar(self.screen)

    def __consume_boss_stage_notice(self):
        """消费 Boss 阶段提示，清空现场弹幕并启动转阶段视觉效果。"""
        for enemy in self.enemy_group:
            if isinstance(enemy, Boss) and enemy.stage_notice is not None:
                self.stage_notice_text = "STAGE " + str(enemy.stage_notice)
                self.stage_notice_start = pygame.time.get_ticks()
                self.phase_wave_start = self.stage_notice_start
                self.enemy_bullet_group.empty()
                self.danmaku_group.empty()
                enemy.music_boom.play()
                enemy.stage_notice = None

    def __draw_stage_notice(self):
        """在屏幕中央快速闪烁绘制 STAGE X 字幕。"""
        if not self.stage_notice_text:
            return

        elapsed = pygame.time.get_ticks() - self.stage_notice_start
        if elapsed >= self.stage_notice_duration:
            self.stage_notice_text = None
            return

        progress = elapsed / self.stage_notice_duration
        alpha = 255 if int(progress * 12) % 2 == 0 else 65
        alpha = max(0, min(255, alpha))

        image = self.stage_font.render(self.stage_notice_text, True, (255, 245, 245))
        image.set_alpha(alpha)
        rect = image.get_rect(center=SCREEN_RECT.center)
        self.screen.blit(image, rect)

    def __draw_phase_wave(self):
        """绘制从屏幕中心快速扩大的转阶段环形波。"""
        if not self.phase_wave_start:
            return

        elapsed = pygame.time.get_ticks() - self.phase_wave_start
        if elapsed >= self.phase_wave_duration:
            self.phase_wave_start = 0
            return

        progress = elapsed / self.phase_wave_duration
        alpha = max(0, int(210 * (1 - progress)))
        radius = int(20 + progress * 420)
        wave = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
        for offset, width in ((0, 5), (18, 3), (36, 2)):
            current_radius = radius + offset
            if current_radius > 0:
                pygame.draw.circle(wave, (255, 245, 245, max(0, alpha - offset * 3)),
                                   SCREEN_RECT.center, current_radius, width)
        self.screen.blit(wave, (0, 0))

    def __check_boss_clear(self):
        """检测 Boss 击破动画是否结束并进入通关界面。"""
        if self.boss_mode and hasattr(self, "boss") and self.boss.clear_complete:
            self.__finish_game_clear()

    def __limit_danmaku_bullets(self):
        """弹幕超上限时优先清理距离屏幕中心最远的子弹。"""
        bullet_count = len(self.danmaku_group)
        if bullet_count <= MAX_DANMAKU_BULLETS:
            return

        remove_count = max(1, int(bullet_count * DANMAKU_REMOVE_RATE), bullet_count - MAX_DANMAKU_BULLETS)
        center_x, center_y = SCREEN_RECT.center
        bullets = sorted(self.danmaku_group,
                         key=lambda bullet: (bullet.rect.centerx - center_x) ** 2 +
                                            (bullet.rect.centery - center_y) ** 2,
                         reverse=True)
        for bullet in bullets[:remove_count]:
            bullet.kill()

    def score_show(self):
        """绘制当前分数。"""
        score_font = pygame.font.Font("./STCAIYUN.ttf", 33)
        image = score_font.render("SCORE:" + str(int(self.score.getvalue())), True, color_gray)
        rect = image.get_rect()
        rect.bottom, rect.right = 700, 480
        self.screen.blit(image, rect)

    def buff_level_show(self):
        """绘制当前子弹等级。"""
        level = min(self.hero.buff1_num + 1, MAX_BULLET_LEVEL)
        image = self.buff_font.render("LV." + str(level), True, color_gray)
        rect = image.get_rect()
        rect.left, rect.top = 12, 12
        self.screen.blit(image, rect)

    def hp_show(self):
        """绘制英雄当前生命值。"""
        hp = max(0, int(round(self.hero.bar.length / self.hero.bar.weight)))
        max_hp = int(self.hero.bar.value)
        image = self.buff_font.render("HP:" + str(hp) + "/" + str(max_hp), True, color_gray)
        rect = image.get_rect()
        rect.left, rect.bottom = 12, SCREEN_RECT.bottom - 12
        self.screen.blit(image, rect)

    def __draw_damage_flash(self):
        """绘制英雄受伤后的红色全屏闪烁。"""
        remaining = self.damage_flash_end - pygame.time.get_ticks()
        if remaining <= 0:
            return

        alpha = max(0, min(130, int(130 * remaining / 180)))
        overlay = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
        overlay.fill((255, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

    @staticmethod
    def __select_difficulty():
        """显示中文难度选择界面并返回所选难度。"""
        screen = pygame.display.set_mode(SCREEN_RECT.size)
        clock = pygame.time.Clock()
        def make_font(size, bold=False):
            font_path = pygame.font.match_font(["simsun", "nsimsun", "microsoftyahei", "simhei", "arial"],
                                               bold=bold)
            if font_path:
                return pygame.font.Font(font_path, size)
            return pygame.font.Font("./STCAIYUN.ttf", size)

        title_font = make_font(42, True)
        option_font = make_font(32, True)
        hint_font = make_font(20)
        help_font = make_font(18)
        bg_image = pygame.image.load("./images/background.png")
        show_help = False

        options = [
            ("normal", "普通", "生命24  BOSS弹幕密度较高"),
            ("hard", "困难", "生命20  BOSS弹幕密度高"),
            ("lunatic", "疯狂", "生命12  高难BOSS弹幕"),
        ]
        buttons = []
        for index, option in enumerate(options):
            rect = pygame.Rect(55, 235 + index * 88, 370, 64)
            buttons.append((rect, option))
        help_rect = pygame.Rect(150, 594, 180, 42)
        help_panel_rect = pygame.Rect(45, 155, 390, 390)
        help_close_rect = pygame.Rect(170, 505, 140, 40)
        help_lines = [
            "移动：方向键 / WASD",
            "低速模式：按住X键，显示中心判定点，",
            "           玩家进入低速移动便于躲避",
            "注意玩家飞机大小远大于实际受击判定区域",
            "暂停：P",
            "目标：躲避弹幕，击破首领",
            "触碰随机投放的空投以升级子弹强度",
        ]

        while True:
            clock.tick(FRAME_PER_SEC)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if show_help:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        show_help = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        if help_close_rect.collidepoint(pos):
                            show_help = False
                    continue

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        return "normal"
                    elif event.key == pygame.K_2:
                        return "hard"
                    elif event.key == pygame.K_3:
                        return "lunatic"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if help_rect.collidepoint(pos):
                        show_help = True
                        continue
                    for rect, option in buttons:
                        if rect.collidepoint(pos):
                            return option[0]

            screen.blit(bg_image, (0, 0))
            overlay = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 125))
            screen.blit(overlay, (0, 0))

            title = title_font.render("难度选择", True, color_gray)
            title_rect = title.get_rect(center=(SCREEN_RECT.centerx, 155))
            screen.blit(title, title_rect)
            pygame.display.set_caption("弹幕飞机大战-难度选择")

            mouse_pos = pygame.mouse.get_pos()
            for rect, option in buttons:
                key, label, desc = option
                hovered = rect.collidepoint(mouse_pos)
                color = (90, 35, 45, 210) if hovered else (35, 35, 45, 190)
                border = (255, 90, 100) if hovered else (180, 180, 190)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, border, rect, 2)

                label_image = option_font.render(label, True, color_gray)
                label_rect = label_image.get_rect(midleft=(rect.left + 24, rect.centery - 10))
                screen.blit(label_image, label_rect)

                desc_image = hint_font.render(desc, True, (210, 215, 220))
                desc_rect = desc_image.get_rect(midleft=(rect.left + 24, rect.centery + 18))
                screen.blit(desc_image, desc_rect)

            hint = hint_font.render("按1/2/3或点击选择", True, (220, 220, 225))
            hint_rect = hint.get_rect(center=(SCREEN_RECT.centerx, 552))
            screen.blit(hint, hint_rect)

            help_hovered = help_rect.collidepoint(mouse_pos)
            help_color = (70, 60, 70, 220) if help_hovered else (35, 35, 45, 200)
            help_border = (235, 235, 245) if help_hovered else (165, 165, 180)
            pygame.draw.rect(screen, help_color, help_rect)
            pygame.draw.rect(screen, help_border, help_rect, 2)
            help_image = hint_font.render("操作说明", True, color_gray)
            help_image_rect = help_image.get_rect(center=help_rect.center)
            screen.blit(help_image, help_image_rect)

            if show_help:
                modal_overlay = pygame.Surface(SCREEN_RECT.size, pygame.SRCALPHA)
                modal_overlay.fill((0, 0, 0, 120))
                screen.blit(modal_overlay, (0, 0))
                pygame.draw.rect(screen, (30, 30, 38), help_panel_rect)
                pygame.draw.rect(screen, (230, 230, 240), help_panel_rect, 2)

                help_title = option_font.render("操作说明", True, color_gray)
                help_title_rect = help_title.get_rect(center=(SCREEN_RECT.centerx, help_panel_rect.top + 42))
                screen.blit(help_title, help_title_rect)

                for index, line in enumerate(help_lines):
                    line_image = help_font.render(line, True, (225, 230, 235))
                    line_rect = line_image.get_rect(midleft=(help_panel_rect.left + 42,
                                                            help_panel_rect.top + 100 + index * 38))
                    screen.blit(line_image, line_rect)

                pygame.draw.rect(screen, (70, 60, 70), help_close_rect)
                pygame.draw.rect(screen, (230, 230, 240), help_close_rect, 2)
                close_image = hint_font.render("返回", True, color_gray)
                close_rect = close_image.get_rect(center=help_close_rect.center)
                screen.blit(close_image, close_rect)
            pygame.display.update()

    @staticmethod
    def __start__():
        """选择难度后创建并启动游戏。"""
        difficulty = PlaneGame.__select_difficulty()
        # 创建游戏对象
        game = PlaneGame(difficulty)

        # 启动游戏
        game.start_game()


if __name__ == '__main__':
    PlaneGame.__start__()
