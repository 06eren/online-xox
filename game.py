import pygame
import sys
import random
import time
from firebase_admin import db
import threading

def close_listener_async(listener):
    if listener:
        try:
            threading.Thread(target=listener.close, daemon=True).start()
        except:
            pass

oda_veri = None

def apply_update(data, path, value):
    if path == '/' or path == '':
        return value
    if data is None:
        data = {}
    keys = [k for k in path.split('/') if k]
    curr = data
    for k in keys[:-1]:
        if k not in curr or not isinstance(curr[k], dict):
            curr[k] = {}
        curr = curr[k]
    if value is None:
        if isinstance(curr, dict): curr.pop(keys[-1], None)
    else:
        curr[keys[-1]] = value
    return data

def on_oda_degisti(event):
    global oda_veri
    if event.event_type == 'put':
        if event.path == '/':
            oda_veri = event.data
        else:
            oda_veri = apply_update(oda_veri, event.path, event.data)
    elif event.event_type == 'patch':
        base_path = event.path if event.path != '/' else ''
        for rel_path, val in event.data.items():
            oda_veri = apply_update(oda_veri, f"{base_path}/{rel_path}", val)

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

class HareketliEmoji:
    def __init__(self, emoji_txt, x, y):
        self.txt = emoji_txt
        self.x = x
        self.y = y
        self.vy = -3
        self.alpha = 255
        self.size = 50
    
    def update(self):
        self.y += self.vy
        self.alpha -= 3

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

def oyunu_baslat(ekran, kullanici_adi, aktif_oda_kodu, benim_siram, ses_acik):
    global oda_veri
    oda_veri = None

    GENISLIK, YUKSEKLIK = ekran.get_width(), ekran.get_height()
    
    font_isimleri = pygame.font.get_fonts()
    secili_font = "impact" if "impact" in font_isimleri else ("arialblack" if "arialblack" in font_isimleri else None)
    font_baslik = pygame.font.SysFont(secili_font, 40)
    font_normal = pygame.font.SysFont(secili_font, 28)
    font_kucuk = pygame.font.SysFont(secili_font, 18)
    font_emoji = pygame.font.SysFont("segoeuiemoji", 30) # Windows için emojileri destekleyen font

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

    oda_ref = db.reference(f'odalar/{aktif_oda_kodu}')
    oda_baslangic = oda_ref.get()
    
    if not oda_baslangic: return
    oda_veri = oda_baslangic
    
    n = oda_veri.get('masa_boyutu', 3)
    hedef_tur = oda_veri.get('toplam_el', 3)
    target = 3 if n == 3 else 4 # 3x3 için 3, 4x4 ve 5x5 için 4 yan yana

    KUTU_BOYUT = 400 // n
    OFFSET_X = (GENISLIK - (n * KUTU_BOYUT)) // 2 - 100 # Sola kaydır
    OFFSET_Y = 100

    listener = oda_ref.listen(on_oda_degisti)

    if 'tahta' not in oda_veri:
        if benim_siram == 'oyuncu1':
            oda_ref.update({'tahta': ['' for _ in range(n*n)], 'sira': 'oyuncu1'})

    konfetiler = []
    hareketli_emojiler = []
    sallanma_miktari = 0
    son_islenen_chat_id = ""
    
    temp_surface = pygame.Surface((GENISLIK, YUKSEKLIK))

    chat_input = ""
    chat_aktif = False
    
    mac_bitti_efekti_oynadi = False
    profil_guncellendi = False
    el_bitis_local = 0

    while True:
        if not oda_veri or not isinstance(oda_veri, dict):
            break

        su_an = pygame.time.get_ticks()
        
        tahta = oda_veri.get('tahta', ['' for _ in range(n*n)])
        sira = oda_veri.get('sira', 'oyuncu1')
        skor = oda_veri.get('skor', {'oyuncu1': 0, 'oyuncu2': 0})
        mevcut_el = oda_veri.get('mevcut_el', 1)
        el_durumu = oda_veri.get('el_durumu', 'oynaniyor')
        kazanan = oda_veri.get('kazanan', None)
        
        hedef_skor = (hedef_tur // 2) + 1
        mac_bitti = skor.get('oyuncu1', 0) >= hedef_skor or skor.get('oyuncu2', 0) >= hedef_skor

        if mac_bitti and not profil_guncellendi:
            profil_guncellendi = True
            user_ref = db.reference(f'kullanicilar/{kullanici_adi}')
            ud = user_ref.get() or {}
            if skor.get(benim_siram, 0) >= hedef_skor:
                ud['kazanma'] = ud.get('kazanma', 0) + 1
            else:
                ud['kaybetme'] = ud.get('kaybetme', 0) + 1
            user_ref.update(ud)

        chat_gecmisi = oda_veri.get('chat', {})
        if chat_gecmisi and isinstance(chat_gecmisi, dict):
            son_key = list(chat_gecmisi.keys())[-1]
            son_mesaj = chat_gecmisi[son_key]
            if son_key != son_islenen_chat_id:
                son_islenen_chat_id = son_key
                if "|EMOJI|" in son_mesaj:
                    gonderen, emj = son_mesaj.split("|EMOJI|")
                    gonderen_sira = 'oyuncu1' if gonderen.strip() == oda_veri['oyuncular']['oyuncu1'] else 'oyuncu2'
                    # Emoji animasyonunu fırlat (ben attıysam sol alttan, o attıysa sağ alttan vb. veya ekranda belirsin)
                    ex = OFFSET_X + 200
                    ey = OFFSET_Y + 200
                    hareketli_emojiler.append(HareketliEmoji(emj.strip(), ex, ey))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if listener: close_listener_async(listener)
                if benim_siram == 'oyuncu1': oda_ref.delete()
                else: oda_ref.child('oyuncular/oyuncu2').delete()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                # Ayrıl Butonu
                if 20 <= pos[0] <= 140 and 20 <= pos[1] <= 60:
                    if listener: close_listener_async(listener)
                    if benim_siram == 'oyuncu1': oda_ref.delete()
                    else: oda_ref.child('oyuncular/oyuncu2').delete()
                    return
                
                # Chat Aktifleştirme
                if GENISLIK - 350 <= pos[0] <= GENISLIK - 20 and YUKSEKLIK - 60 <= pos[1] <= YUKSEKLIK - 20:
                    chat_aktif = True
                else:
                    chat_aktif = False

                # Emojiler (Gülme, Kızma vb. 4 emoji butonu)
                emoji_list = ["😂", "😠", "😭", "🎯"]
                CHAT_X = GENISLIK - 350
                for i, emj in enumerate(emoji_list):
                    ex = CHAT_X + 20 + (i * 70)
                    ey = 100
                    if ex <= pos[0] <= ex + 55 and ey <= pos[1] <= ey + 50:
                        oda_ref.child('chat').push(f"{kullanici_adi}|EMOJI|{emj}")

                # Tahta hamlesi
                if el_durumu == 'oynaniyor' and sira == benim_siram and not mac_bitti:
                    col = (pos[0] - OFFSET_X) // KUTU_BOYUT
                    row = (pos[1] - OFFSET_Y) // KUTU_BOYUT
                    
                    if 0 <= col < n and 0 <= row < n:
                        idx = row * n + col
                        if tahta[idx] == '':
                            yeni_tahta = tahta.copy()
                            yeni_tahta[idx] = benim_siram
                            
                            if benim_siram == 'oyuncu1': play_sound(ses_place_x)
                            else: play_sound(ses_place_o)

                            k = check_win_dynamic(yeni_tahta, n, target)
                            if k:
                                yeni_skor = skor.copy()
                                if k != 'draw': yeni_skor[k] += 1
                                oda_ref.update({'tahta': yeni_tahta, 'el_durumu': 'bitti', 'kazanan': k, 'skor': yeni_skor, 'el_bitis_zamani': int(time.time())})
                            else:
                                siradaki = 'oyuncu2' if benim_siram == 'oyuncu1' else 'oyuncu1'
                                oda_ref.update({'tahta': yeni_tahta, 'sira': siradaki})
            
            if event.type == pygame.KEYDOWN and chat_aktif:
                if event.key == pygame.K_RETURN:
                    if chat_input.strip():
                        oda_ref.child('chat').push(f"{kullanici_adi}: {chat_input.strip()}")
                        chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                else:
                    if len(chat_input) < 30:
                        chat_input += event.unicode

        if el_durumu == 'bitti' and not mac_bitti:
            if el_bitis_local == 0:
                el_bitis_local = su_an
                
            if not mac_bitti_efekti_oynadi:
                mac_bitti_efekti_oynadi = True
                if kazanan == benim_siram:
                    play_sound(ses_win)
                    for _ in range(150): konfetiler.append(Confetti(GENISLIK//2, YUKSEKLIK))
                elif kazanan and kazanan != 'draw':
                    play_sound(ses_lose)
                    sallanma_miktari = 20

            if benim_siram == 'oyuncu1' and el_bitis_local > 0 and su_an - el_bitis_local > 3000:
                oda_ref.update({
                    'tahta': ['' for _ in range(n*n)],
                    'sira': 'oyuncu1',
                    'el_durumu': 'oynaniyor',
                    'kazanan': None,
                    'mevcut_el': mevcut_el + 1
                })
                el_bitis_local = 0
        elif el_durumu == 'oynaniyor':
            el_bitis_local = 0
            mac_bitti_efekti_oynadi = False

        temp_surface.fill((15, 15, 20))

        # Ayrıl Butonu
        pygame.draw.rect(temp_surface, (255, 80, 80), (20, 20, 120, 40), border_radius=8)
        btn_yazi = font_normal.render("Ayrıl", True, (255, 255, 255))
        temp_surface.blit(btn_yazi, btn_yazi.get_rect(center=(80, 40)))

        # Skorlar
        p1_isim = oda_veri['oyuncular'].get('oyuncu1', '1. Oyuncu')
        p2_isim = oda_veri['oyuncular'].get('oyuncu2', '2. Oyuncu')
        skor_yazi = font_baslik.render(f"{p1_isim} (X)   {skor.get('oyuncu1',0)} - {skor.get('oyuncu2',0)}   {p2_isim} (O)", True, (255, 215, 0))
        temp_surface.blit(skor_yazi, skor_yazi.get_rect(center=(OFFSET_X + (n*KUTU_BOYUT)//2, 50)))

        # Tahta Çizgileri
        for i in range(1, n):
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y + n * KUTU_BOYUT), 6)
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X, OFFSET_Y + i * KUTU_BOYUT), (OFFSET_X + n * KUTU_BOYUT, OFFSET_Y + i * KUTU_BOYUT), 6)

        # X ve O'lar
        for idx, deger in enumerate(tahta):
            x = OFFSET_X + (idx % n) * KUTU_BOYUT + KUTU_BOYUT // 2
            y = OFFSET_Y + (idx // n) * KUTU_BOYUT + KUTU_BOYUT // 2
            
            p = KUTU_BOYUT // 3
            if deger == 'oyuncu1':
                pygame.draw.line(temp_surface, (255, 50, 50), (x-p, y-p), (x+p, y+p), 8)
                pygame.draw.line(temp_surface, (255, 50, 50), (x+p, y-p), (x-p, y+p), 8)
            elif deger == 'oyuncu2':
                pygame.draw.circle(temp_surface, (50, 200, 255), (x, y), int(p*1.2), 8)

        # Durum Yazısı
        if mac_bitti:
            durum_yazi = "MAÇI KAZANDIN!" if skor.get(benim_siram,0) >= hedef_skor else "MAÇI KAYBETTİN!"
            renk = (50, 255, 50) if skor.get(benim_siram,0) >= hedef_skor else (255, 50, 50)
        elif el_durumu == 'bitti':
            if kazanan == 'draw': durum_yazi, renk = "BERABERE!", (200, 200, 200)
            elif kazanan == benim_siram: durum_yazi, renk = "ELİ KAZANDIN!", (50, 255, 50)
            else: durum_yazi, renk = "ELİ KAYBETTİN!", (255, 50, 50)
        else:
            durum_yazi = "Sıra Sende!" if sira == benim_siram else "Rakip Bekleniyor..."
            renk = (50, 255, 50) if sira == benim_siram else (200, 200, 200)
            
        bilgi = font_baslik.render(durum_yazi, True, renk)
        temp_surface.blit(bilgi, bilgi.get_rect(center=(OFFSET_X + (n*KUTU_BOYUT)//2, YUKSEKLIK - 50)))

        # SOHBET BÖLÜMÜ (Sağ Taraf)
        CHAT_X = GENISLIK - 350
        CHAT_Y = 160
        CHAT_W = 330
        pygame.draw.rect(temp_surface, (30, 30, 35), (CHAT_X, CHAT_Y, CHAT_W, 370), border_radius=10)
        
        # Emoji Butonları Çizimi
        emoji_list = ["😂", "😠", "😭", "🎯"]
        for i, emj in enumerate(emoji_list):
            ex = CHAT_X + 20 + (i * 70)
            ey = 100
            pygame.draw.rect(temp_surface, (50, 50, 60), (ex, ey, 55, 50), border_radius=10)
            e_surf = font_emoji.render(emj, True, (255, 255, 255))
            temp_surface.blit(e_surf, e_surf.get_rect(center=(ex+27, ey+25)))

        chat_gecmisi = oda_veri.get('chat', {})
        if isinstance(chat_gecmisi, dict):
            mesajlar = list(chat_gecmisi.values())
            # Sadece normal metinleri chatte göster
            metin_mesajlar = [m for m in mesajlar if "|EMOJI|" not in m][-8:]
            my_offset = CHAT_Y + 10
            for m in metin_mesajlar:
                renk_m = (150, 255, 150) if m.startswith(kullanici_adi) else (255, 255, 255)
                ms = font_kucuk.render(m[:35], True, renk_m)
                temp_surface.blit(ms, (CHAT_X + 10, my_offset))
                my_offset += 30

        # Chat İnput Kutusu
        input_rect = pygame.Rect(CHAT_X + 10, YUKSEKLIK - 60, CHAT_W - 20, 40)
        pygame.draw.rect(temp_surface, (70, 70, 80) if chat_aktif else (50, 50, 60), input_rect, border_radius=5)
        placeholder = chat_input if chat_aktif else (chat_input if chat_input else "Mesaj yaz (Enter)")
        ip_surf = font_kucuk.render(placeholder, True, (255, 255, 255) if chat_aktif else (150, 150, 150))
        temp_surface.blit(ip_surf, (input_rect.x + 10, input_rect.y + 10))

        # Efektler
        for k in konfetiler[:]:
            k.update()
            k.draw(temp_surface)
            if k.y > YUKSEKLIK: konfetiler.remove(k)

        for he in hareketli_emojiler[:]:
            he.update()
            emj_surf = font_emoji.render(he.txt, True, (255, 255, 255))
            emj_surf.set_alpha(he.alpha)
            temp_surface.blit(emj_surf, emj_surf.get_rect(center=(he.x, he.y)))
            if he.alpha <= 0: hareketli_emojiler.remove(he)

        offset_x, offset_y = 0, 0
        if sallanma_miktari > 0:
            offset_x = random.randint(-sallanma_miktari, sallanma_miktari)
            offset_y = random.randint(-sallanma_miktari, sallanma_miktari)
            sallanma_miktari -= 1

        ekran.fill((0, 0, 0))
        ekran.blit(temp_surface, (offset_x, offset_y))
        
        # Watermark
        watermark = font_kucuk.render("Developed By: ERN YAZILIM", True, (100, 100, 100))
        ekran.blit(watermark, (GENISLIK - watermark.get_width() - 10, YUKSEKLIK - watermark.get_height() - 10))
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)

    if listener:
        close_listener_async(listener)