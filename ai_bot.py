import pygame
import sys
import random

class Confetti:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-15, -5)
        self.color = random.choice([(255,50,50), (50,255,50), (50,50,255), (255,255,50), (255,50,255), (50,255,255), (255,150,50)])
        self.size = random.randint(5, 10)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-10, 10)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5 
        self.angle += self.rot_speed

    def draw(self, surface):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill(self.color)
        s = pygame.transform.rotate(s, self.angle)
        surface.blit(s, (self.x, self.y))

def check_win_dynamic(board, n, target):
    def get_cell(r, c):
        return board[r * n + c]
    for r in range(n):
        for c in range(n):
            val = get_cell(r, c)
            if val == '': continue
            if c <= n - target and all(get_cell(r, c+i) == val for i in range(target)): return val
            if r <= n - target and all(get_cell(r+i, c) == val for i in range(target)): return val
            if c <= n - target and r <= n - target and all(get_cell(r+i, c+i) == val for i in range(target)): return val
            if c >= target - 1 and r <= n - target and all(get_cell(r+i, c-i) == val for i in range(target)): return val
    if '' not in board: return 'draw'
    return None

def ai_move(board, n, target, zorluk='normal', bot_symbol='oyuncu2', human_symbol='oyuncu1'):
    empty_spots = [i for i, x in enumerate(board) if x == '']
    if not empty_spots: return None

    if zorluk == 'kolay':
        if random.random() < 0.4:
            return random.choice(empty_spots)
            
    if zorluk in ['normal', 'zor']:
        # 1. Kazanabiliyor muyuz?
        for i in empty_spots:
            board[i] = bot_symbol
            if check_win_dynamic(board, n, target) == bot_symbol:
                board[i] = ''
                return i
            board[i] = ''
            
        # 2. İnsan kazanıyor mu? Engelle!
        for i in empty_spots:
            board[i] = human_symbol
            if check_win_dynamic(board, n, target) == human_symbol:
                board[i] = ''
                # Normal modda ufak bir hata payı (engellemeyi kaçırma)
                if zorluk == 'normal' and random.random() < 0.2:
                    break
                return i
            board[i] = ''

    if zorluk == 'zor':
        # Merkez veya köşeleri al
        center = (n*n) // 2
        if board[center] == '': return center
        if n == 3:
            corners = [0, 2, 6, 8]
            avail_corners = [c for c in corners if board[c] == '']
            if avail_corners: return random.choice(avail_corners)

    return random.choice(empty_spots)

def botla_oyna(ekran, masa_boyutu, hedef_tur, ses_acik, zorluk='normal'):
    GENISLIK, YUKSEKLIK = ekran.get_width(), ekran.get_height()
    n = masa_boyutu
    target = 3 if n == 3 else 4
    KUTU_BOYUT = 400 // n
    OFFSET_X = (GENISLIK - (n * KUTU_BOYUT)) // 2
    OFFSET_Y = 100
    
    font_isimleri = pygame.font.get_fonts()
    secili_font = "impact" if "impact" in font_isimleri else ("arialblack" if "arialblack" in font_isimleri else None)
    font_baslik = pygame.font.SysFont(secili_font, 40)
    font_normal = pygame.font.SysFont(secili_font, 28)

    ses_place_x = ses_place_o = ses_win = ses_lose = None
    if ses_acik:
        try:
            ses_place_x = pygame.mixer.Sound("place_x.wav")
            ses_place_o = pygame.mixer.Sound("place_o.wav")
            ses_win = pygame.mixer.Sound("win.wav")
            ses_lose = pygame.mixer.Sound("lose.wav")
        except: pass

    def play_sound(sound):
        if ses_acik and sound:
            try: sound.play()
            except: pass

    board = ['' for _ in range(n*n)]
    sira = 'oyuncu1'
    skor = {'oyuncu1': 0, 'bot': 0}
    hedef_skor = (hedef_tur // 2) + 1
    
    sallanma_miktari = 0
    konfetiler = []
    el_durumu = 'oynaniyor'
    el_sonu_zamani = 0
    mac_bitti = False
    mac_bitti_zamani = 0
    kazanan = None

    temp_surface = pygame.Surface((GENISLIK, YUKSEKLIK))
    
    bot_dusunme_zamani = 0
    
    while True:
        su_an = pygame.time.get_ticks()
        
        if el_durumu == 'oynaniyor':
            k = check_win_dynamic(board, n, target)
            if k:
                kazanan = k
                el_durumu = 'bitti'
                el_sonu_zamani = su_an
                if kazanan == 'oyuncu1': 
                    skor['oyuncu1'] += 1
                    play_sound(ses_win)
                    for _ in range(150): konfetiler.append(Confetti(GENISLIK//2, YUKSEKLIK))
                elif kazanan == 'oyuncu2':
                    skor['bot'] += 1
                    play_sound(ses_lose)
                    sallanma_miktari = 20
        
        if el_durumu == 'oynaniyor' and sira == 'oyuncu2':
            if bot_dusunme_zamani == 0:
                bot_dusunme_zamani = su_an + random.randint(400, 800)
            elif su_an > bot_dusunme_zamani:
                move = ai_move(board, n, target, zorluk)
                if move is not None:
                    board[move] = 'oyuncu2'
                    play_sound(ses_place_o)
                sira = 'oyuncu1'
                bot_dusunme_zamani = 0

        if el_durumu == 'bitti' and su_an - el_sonu_zamani > 3000 and not mac_bitti:
            if skor['oyuncu1'] >= hedef_skor or skor['bot'] >= hedef_skor:
                mac_bitti = True
                mac_bitti_zamani = su_an
            else:
                board = ['' for _ in range(n*n)]
                sira = 'oyuncu1'
                el_durumu = 'oynaniyor'
                kazanan = None

        if mac_bitti and su_an - mac_bitti_zamani > 4000:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and sira == 'oyuncu1' and el_durumu == 'oynaniyor':
                pos = pygame.mouse.get_pos()
                if 20 <= pos[0] <= 140 and 20 <= pos[1] <= 60:
                    return # Ayrıl
                    
                col = (pos[0] - OFFSET_X) // KUTU_BOYUT
                row = (pos[1] - OFFSET_Y) // KUTU_BOYUT
                
                if 0 <= col < n and 0 <= row < n:
                    idx = row * n + col
                    if board[idx] == '':
                        board[idx] = 'oyuncu1'
                        sira = 'oyuncu2'
                        play_sound(ses_place_x)

        temp_surface.fill((15, 15, 20))
        
        pygame.draw.rect(temp_surface, (255, 80, 80), (20, 20, 120, 40), border_radius=8)
        btn_yazi = font_normal.render("Ayrıl", True, (255, 255, 255))
        temp_surface.blit(btn_yazi, btn_yazi.get_rect(center=(80, 40)))

        skor_yazi = font_baslik.render(f"Sen (X)   {skor['oyuncu1']} - {skor['bot']}   Bot (O)", True, (255, 215, 0))
        temp_surface.blit(skor_yazi, skor_yazi.get_rect(center=(GENISLIK // 2, 50)))
        
        for i in range(1, n):
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y + n * KUTU_BOYUT), 6)
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X, OFFSET_Y + i * KUTU_BOYUT), (OFFSET_X + n * KUTU_BOYUT, OFFSET_Y + i * KUTU_BOYUT), 6)

        for idx, deger in enumerate(board):
            x = OFFSET_X + (idx % n) * KUTU_BOYUT + KUTU_BOYUT // 2
            y = OFFSET_Y + (idx // n) * KUTU_BOYUT + KUTU_BOYUT // 2
            
            p = KUTU_BOYUT // 3
            if deger == 'oyuncu1':
                pygame.draw.line(temp_surface, (255, 50, 50), (x-p, y-p), (x+p, y+p), 8)
                pygame.draw.line(temp_surface, (255, 50, 50), (x+p, y-p), (x-p, y+p), 8)
            elif deger == 'oyuncu2':
                pygame.draw.circle(temp_surface, (50, 200, 255), (x, y), int(p*1.2), 8)

        if mac_bitti:
            durum_yazi = "MAÇI KAZANDIN!" if skor['oyuncu1'] >= hedef_skor else "MAÇI KAYBETTİN!"
            renk = (50, 255, 50) if skor['oyuncu1'] >= hedef_skor else (255, 50, 50)
        elif el_durumu == 'bitti':
            if kazanan == 'draw': durum_yazi, renk = "BERABERE!", (200, 200, 200)
            elif kazanan == 'oyuncu1': durum_yazi, renk = "ELİ KAZANDIN!", (50, 255, 50)
            else: durum_yazi, renk = "ELİ KAYBETTİN!", (255, 50, 50)
        else:
            durum_yazi = "Sıra Sende!" if sira == 'oyuncu1' else "Bot Düşünüyor..."
            renk = (50, 255, 50) if sira == 'oyuncu1' else (200, 200, 200)
            
        bilgi = font_baslik.render(durum_yazi, True, renk)
        temp_surface.blit(bilgi, bilgi.get_rect(center=(GENISLIK // 2, YUKSEKLIK - 50)))

        for k in konfetiler[:]:
            k.update()
            k.draw(temp_surface)
            if k.y > YUKSEKLIK: konfetiler.remove(k)

        offset_x, offset_y = 0, 0
        if sallanma_miktari > 0:
            offset_x = random.randint(-sallanma_miktari, sallanma_miktari)
            offset_y = random.randint(-sallanma_miktari, sallanma_miktari)
            sallanma_miktari -= 1

        ekran.fill((0, 0, 0))
        ekran.blit(temp_surface, (offset_x, offset_y))
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)
