import pygame
import random
import time
import pyautogui
import win32gui
import win32con

# 初始化设置
pygame.init()
pygame.mixer.init()

# 窗口配置
SCORE_AREA_HEIGHT = 100
SIDEBAR_WIDTH = 400
GRID_SIZE = 10
IMAGE_SIZE = 130
WIDTH = SIDEBAR_WIDTH * 2 + GRID_SIZE * IMAGE_SIZE
HEIGHT = SCORE_AREA_HEIGHT + GRID_SIZE * IMAGE_SIZE
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("抽象消消乐")

# 获取窗口位置
try:
    hwnd = win32gui.FindWindow(None, "抽象消消乐")
    rect = win32gui.GetWindowRect(hwnd)
    WIN_X, WIN_Y = rect[0], rect[1]
except:
    WIN_X, WIN_Y = 0, 0

# 字体配置
pygame.font.init()
SCORE_FONT = pygame.font.SysFont('Arial', 50, bold=True)
BOARD_FONT = pygame.font.SysFont('Arial', 30)
BOARD_COLOR = (0, 0, 0)
# ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ 信息版字体配置（在此修改）↓↓↓↓↓↓↓↓↓↓↓↓↓
INFO_FONT_SIZE = 40  # 字体大小（建议28-36）
INFO_TEXT_COLOR = (30, 30, 30)  # RGB颜色值
# 使用中文字体文件（需要将simhei.ttf放在项目目录）
INFO_FONT = pygame.font.Font('simhei.ttf', INFO_FONT_SIZE)
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

# ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ 在此编辑信息版内容（支持换行）↓↓↓↓↓↓↓↓↓↓↓↓↓
INFO_TEXT = """欢迎来到抽象消消乐：
1.打不到目标不下波
2.关注=目标＋100
3.小心心=目标+1000
4.墨镜=定制图片语音
5.学习可咨讯 
text in 25.4.23



"""
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑


# 资源加载
def load_resources():
    global sound_mapping, images
    # 声音加载
    sound_mapping = {}
    try:
        for i in range(5):
            sound_mapping[i] = pygame.mixer.Sound(f"wav/{i}.WAV")
    except Exception as e:
        print(f"声音加载失败: {e}")
        pygame.quit()
        exit()

    # 图片加载
    try:
        images = [pygame.transform.scale(pygame.image.load(f"pic/nezha/{i}.png"),
                         (IMAGE_SIZE, IMAGE_SIZE)) for i in range(5)]
    except Exception as e:
        print(f"图片加载失败: {e}")
        pygame.quit()
        exit()


load_resources()

# 游戏参数
MOUSE_MOVE_DURATION = 0.2
CLICK_INTERVAL = 0.15
REACTION_TIME = 0.2


class GameState:
    def __init__(self):
        self.board = []
        self.animation_state = "IDLE"
        self.animation_start_time = 0
        self.swap_positions = []
        self.falling_blocks = []
        self.score = 0
        self.target_score = 1000
        self.auto_mode = True
        self.emergency_stop = False
        self.selected = None
        self.board_text = ""

        self.reset_board()

    def reset_board(self):
        def create_valid_board():
            while True:
                board = [[random.randint(0, 4) for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                if not self.find_matches(board):
                    return board

        self.board = create_valid_board()

    def find_matches(self, board):
        matches = []
        # 横向检测
        for r in range(GRID_SIZE):
            c = 0
            while c < GRID_SIZE - 2:
                if board[r][c] is None:
                    c += 1
                    continue
                current = board[r][c]
                length = 1
                while c + length < GRID_SIZE and board[r][c + length] == current:
                    length += 1
                if length >= 3:
                    matches.append([(r, c + i) for i in range(length)])
                    c += length
                else:
                    c += 1
        # 纵向检测
        for c in range(GRID_SIZE):
            r = 0
            while r < GRID_SIZE - 2:
                if board[r][c] is None:
                    r += 1
                    continue
                current = board[r][c]
                length = 1
                while r + length < GRID_SIZE and board[r + length][c] == current:
                    length += 1
                if length >= 3:
                    matches.append([(r + i, c) for i in range(length)])
                    r += length
                else:
                    r += 1
        return matches

    def find_all_swaps(self):
        valid_swaps = []
        # 横向交换检测
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE - 1):
                temp_board = [row[:] for row in self.board]
                temp_board[r][c], temp_board[r][c + 1] = temp_board[r][c + 1], temp_board[r][c]
                if self.find_matches(temp_board):
                    valid_swaps.append(((r, c), (r, c + 1)))
        # 纵向交换检测
        for r in range(GRID_SIZE - 1):
            for c in range(GRID_SIZE):
                temp_board = [row[:] for row in self.board]
                temp_board[r][c], temp_board[r + 1][c] = temp_board[r + 1][c], temp_board[r][c]
                if self.find_matches(temp_board):
                    valid_swaps.append(((r, c), (r + 1, c)))
        return valid_swaps

    def game_to_screen(self, pos):
        r, c = pos
        return (
            WIN_X + SIDEBAR_WIDTH + c * IMAGE_SIZE + IMAGE_SIZE // 2,
            WIN_Y + SCORE_AREA_HEIGHT + r * IMAGE_SIZE + IMAGE_SIZE // 2
        )

    def handle_swap_animation(self, elapsed):
        progress = min(elapsed / 0.3, 1.0)
        (r1, c1), (r2, c2) = self.swap_positions[0]

        dx = int((c2 - c1) * IMAGE_SIZE * progress)
        dy = int((r2 - r1) * IMAGE_SIZE * progress)

        # 绘制带偏移的交换动画
        win.blit(images[self.board[r1][c1]],
                 (SIDEBAR_WIDTH + c1 * IMAGE_SIZE + dx,
                  r1 * IMAGE_SIZE + SCORE_AREA_HEIGHT + dy))
        win.blit(images[self.board[r2][c2]],
                 (SIDEBAR_WIDTH + c2 * IMAGE_SIZE - dx,
                  r2 * IMAGE_SIZE + SCORE_AREA_HEIGHT - dy))

        if progress >= 1.0:
            self.start_clear_animation()

    def start_clear_animation(self):
        matches = self.find_matches(self.board)
        if not matches:
            if self.animation_state == "SWAP_ANIMATION":
                self.start_swap_back()
            else:
                self.animation_state = "IDLE"
            return

        eliminated = set()
        for group in matches:
            for (r, c) in group:
                eliminated.add((r, c))

        # 积分计算
        self.score += min(5, max(3, len(eliminated) // 3))

        # 播放音效
        sound_played = {i: False for i in range(5)}
        for (r, c) in eliminated:
            block_type = self.board[r][c]
            self.board[r][c] = None
            if 0 <= block_type <= 4 and not sound_played[block_type]:
                if sound_mapping.get(block_type):
                    sound_mapping[block_type].play()
                sound_played[block_type] = True

        self.animation_state = "MATCH_ANIMATION"
        self.animation_start_time = time.time()

    def start_fall_animation(self):
        new_board = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.falling_blocks.clear()

        for c in range(GRID_SIZE):
            column = [self.board[r][c] for r in range(GRID_SIZE) if self.board[r][c] is not None]
            new_column = [random.randint(0, 4) for _ in range(GRID_SIZE - len(column))] + column
            for r in range(GRID_SIZE):
                new_board[r][c] = new_column[r]
                if new_column[r] != self.board[r][c]:
                    self.falling_blocks.append({
                        "start": (r - (GRID_SIZE - len(column)), c),
                        "end": (r, c),
                        "value": new_column[r],
                        "progress": 0
                    })

        self.board = new_board
        self.animation_state = "FALL_ANIMATION"
        self.animation_start_time = time.time()

    def start_swap_back(self):
        if not self.swap_positions:
            self.animation_state = "IDLE"
            return
        self.animation_state = "SWAPBACK_ANIMATION"
        self.animation_start_time = time.time()


game_state = GameState()


def human_like_click(start_pos, end_pos):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(REACTION_TIME)

        pyautogui.moveTo(*start_pos, duration=MOUSE_MOVE_DURATION)
        pyautogui.mouseDown()
        time.sleep(CLICK_INTERVAL / 2)
        pyautogui.mouseUp()

        time.sleep(CLICK_INTERVAL)
        pyautogui.moveTo(*end_pos, duration=MOUSE_MOVE_DURATION)
        pyautogui.mouseDown()
        time.sleep(CLICK_INTERVAL / 2)
        pyautogui.mouseUp()
    except Exception as e:
        print(f"操作异常: {e}")


def auto_play():
    valid_swaps = game_state.find_all_swaps()
    if valid_swaps:
        swap = random.choice(valid_swaps)
        pos1, pos2 = swap

        # 更新选中状态
        game_state.selected = pos1

        # 执行交换
        game_state.board[pos1[0]][pos1[1]], game_state.board[pos2[0]][pos2[1]] = \
            game_state.board[pos2[0]][pos2[1]], game_state.board[pos1[0]][pos1[1]]

        screen_pos1 = game_state.game_to_screen(pos1)
        screen_pos2 = game_state.game_to_screen(pos2)

        human_like_click(screen_pos1, screen_pos2)

        game_state.swap_positions = [swap]
        game_state.animation_state = "SWAP_ANIMATION"
        game_state.animation_start_time = time.time()

        # 交换完成后清除选中状态
        game_state.selected = None

        return True
    return False

# 主循环
running = True
clock = pygame.time.Clock()

while running:
    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                game_state.auto_mode = not game_state.auto_mode
                game_state.emergency_stop = True
                print(f"模式切换: {'自动' if game_state.auto_mode else '手动'}")

            # 目标分数调整
            elif event.key == pygame.K_j:
                game_state.target_score += 100
            elif event.key == pygame.K_k:
                game_state.target_score += 500
            elif event.key == pygame.K_l:
                game_state.target_score += 1000
            elif event.key == pygame.K_u:
                game_state.target_score = max(0, game_state.target_score - 100)
            elif event.key == pygame.K_i:
                game_state.target_score = max(0, game_state.target_score - 500)
            elif event.key == pygame.K_o:
                game_state.target_score = max(0, game_state.target_score - 1000)

            # 写字板输入
            elif event.unicode.isprintable():
                game_state.board_text += event.unicode
            elif event.key == pygame.K_BACKSPACE:
                game_state.board_text = game_state.board_text[:-1]

        elif event.type == pygame.MOUSEBUTTONDOWN and not game_state.auto_mode:
            if game_state.animation_state != "IDLE":
                continue

            x, y = event.pos
            y -= SCORE_AREA_HEIGHT
            c = (x - SIDEBAR_WIDTH) // IMAGE_SIZE
            r = y // IMAGE_SIZE

            if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
                continue

            if game_state.selected is None:
                game_state.selected = (r, c)
            else:
                dr = abs(r - game_state.selected[0])
                dc = abs(c - game_state.selected[1])
                if (dr == 1 and dc == 0) or (dc == 1 and dr == 0):
                    temp_board = [row[:] for row in game_state.board]
                    temp1, temp2 = temp_board[game_state.selected[0]][game_state.selected[1]], temp_board[r][c]
                    temp_board[game_state.selected[0]][game_state.selected[1]] = temp2
                    temp_board[r][c] = temp1

                    if not game_state.find_matches(temp_board):
                        game_state.board[game_state.selected[0]][game_state.selected[1]], game_state.board[r][c] = \
                            game_state.board[r][c], game_state.board[game_state.selected[0]][game_state.selected[1]]
                        game_state.swap_positions = [(game_state.selected, (r, c))]
                        game_state.start_swap_back()
                    else:
                        game_state.swap_positions = [(game_state.selected, (r, c))]
                        game_state.board[game_state.selected[0]][game_state.selected[1]], game_state.board[r][c] = \
                            game_state.board[r][c], game_state.board[game_state.selected[0]][game_state.selected[1]]
                        game_state.animation_state = "SWAP_ANIMATION"
                        game_state.animation_start_time = time.time()
                    game_state.selected = None
                else:
                    game_state.selected = (r, c)

    # 游戏逻辑
    if game_state.auto_mode and game_state.animation_state == "IDLE" and not game_state.emergency_stop:
        auto_play()
    else:
        game_state.emergency_stop = False

    # 界面绘制
    win.fill((255, 255, 255))

    # 绘制左边记分板
    pygame.draw.rect(win, (200, 200, 200), (0, 0, SIDEBAR_WIDTH, HEIGHT))
    win.blit(SCORE_FONT.render(f'score: {game_state.score}', True, (255, 255, 255)), (10, 10))
    win.blit(SCORE_FONT.render(f'target score: {game_state.target_score}', True, (255, 0, 0)), (10, 60))

     # ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ 绘制信息版 ↓↓↓↓↓↓↓↓↓↓↓↓↓
    info_y_start = 120  # 信息版起始Y坐标
    line_spacing = 5    # 行间距
    
    # 分割文本为多行
    info_lines = INFO_TEXT.split('\n')
    
    # 逐行渲染文本
    for i, line in enumerate(info_lines):
        text_surface = INFO_FONT.render(line, True, INFO_TEXT_COLOR)
        win.blit(text_surface, (10, info_y_start + i*(INFO_FONT_SIZE+line_spacing)))
    # ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑


    # 绘制右边写字板
    pygame.draw.rect(win, (200, 200, 200), (WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT))
    text_surface = BOARD_FONT.render(game_state.board_text, True, BOARD_COLOR)
    win.blit(text_surface, (WIDTH - SIDEBAR_WIDTH + 20, 10))

    # 绘制游戏区域
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if game_state.board[r][c] is not None:
                x = SIDEBAR_WIDTH + c * IMAGE_SIZE
                y = r * IMAGE_SIZE + SCORE_AREA_HEIGHT
                win.blit(images[game_state.board[r][c]], (x, y))

                # 绘制选中效果
                if game_state.selected == (r, c):
                    pygame.draw.rect(win, (0, 255, 0), (x, y, IMAGE_SIZE, IMAGE_SIZE), 10)

    # 模式提示
    mode_text = SCORE_FONT.render(
        f'[SPACE] : {"manual" if game_state.auto_mode else "manual"}',
        True,
        (255, 0, 0) if game_state.auto_mode else (0, 128, 0)
    )
    win.blit(mode_text, (WIDTH - 300, 10))

    # 动画处理
    if game_state.animation_state != "IDLE":
        elapsed = time.time() - game_state.animation_start_time

        if game_state.animation_state == "SWAP_ANIMATION":
            game_state.handle_swap_animation(elapsed)

        elif game_state.animation_state == "MATCH_ANIMATION":
            if elapsed % 0.2 < 0.1:
                for group in game_state.find_matches(game_state.board):
                    for (r, c) in group:
                        win.blit(images[game_state.board[r][c]],
                                 (SIDEBAR_WIDTH + c * IMAGE_SIZE,
                                  r * IMAGE_SIZE + SCORE_AREA_HEIGHT))
            if elapsed >= 0.5:
                game_state.start_fall_animation()

        elif game_state.animation_state == "FALL_ANIMATION":
            progress = min(elapsed / 0.5, 1.0)
            for block in game_state.falling_blocks:
                start_r, start_c = block["start"]
                end_r, end_c = block["end"]
                y = start_r * IMAGE_SIZE + (end_r - start_r) * IMAGE_SIZE * progress
                win.blit(images[block["value"]],
                         (SIDEBAR_WIDTH + end_c * IMAGE_SIZE,
                          int(y) + SCORE_AREA_HEIGHT))
            if elapsed >= 0.5:
                game_state.animation_state = "IDLE"
                if game_state.find_matches(game_state.board):
                    game_state.start_clear_animation()

        elif game_state.animation_state == "SWAPBACK_ANIMATION":
            progress = min(elapsed / 0.3, 1.0)
            (r1, c1), (r2, c2) = game_state.swap_positions[0]

            dx = int((c2 - c1) * IMAGE_SIZE * (1 - progress))
            dy = int((r2 - r1) * IMAGE_SIZE * (1 - progress))
            win.blit(images[game_state.board[r1][c1]],
                     (SIDEBAR_WIDTH + c1 * IMAGE_SIZE + dx,
                      r1 * IMAGE_SIZE + SCORE_AREA_HEIGHT + dy))
            win.blit(images[game_state.board[r2][c2]],
                     (SIDEBAR_WIDTH + c2 * IMAGE_SIZE - dx,
                      r2 * IMAGE_SIZE + SCORE_AREA_HEIGHT - dy))
            if progress >= 1.0:
                game_state.board[r1][c1], game_state.board[r2][c2] = \
                    game_state.board[r2][c2], game_state.board[r1][c1]
                game_state.animation_state = "IDLE"
                game_state.swap_positions = []

    pygame.display.update()
    clock.tick(60)

pygame.mixer.quit()
pygame.quit()    