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
        self.vy += 0.5 # gravity
        self.angle += self.rot_speed

    def draw(self, surface):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill(self.color)
        s = pygame.transform.rotate(s, self.angle)
        surface.blit(s, (self.x, self.y))

def check_win(board):
    if not board or len(board) < 9: return None
    lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in lines:
        if board[a] != '' and board[a] == board[b] == board[c]:
            return board[a]
    if '' not in board:
        return 'draw'
    return None

def oyunu_baslat(ekran, kullanici_adi, oda_kodu, oyuncu_sirasi, ses_acik):
    global oda_veri
    GENISLIK, YUKSEKLIK = ekran.get_width(), ekran.get_height()
    KUTU_BOYUT = 140
    OFFSET_X = (GENISLIK - (3 * KUTU_BOYUT)) // 2
    OFFSET_Y = 100
    
    font_isimleri = pygame.font.get_fonts()
    secili_font = "impact" if "impact" in font_isimleri else ("arialblack" if "arialblack" in font_isimleri else None)
    font_baslik = pygame.font.SysFont(secili_font, 40)
    font_normal = pygame.font.SysFont(secili_font, 28)

    # Sesleri Yükle
    ses_place_x = ses_place_o = ses_win = ses_lose = None
    if ses_acik:
        try:
            ses_place_x = pygame.mixer.Sound("place_x.wav")
            ses_place_o = pygame.mixer.Sound("place_o.wav")
            ses_win = pygame.mixer.Sound("win.wav")
            ses_lose = pygame.mixer.Sound("lose.wav")
        except:
            pass

    def play_sound(sound):
        if ses_acik and sound:
            try: sound.play()
            except: pass

    oda_ref = db.reference(f'odalar/{oda_kodu}')
    oda_veri = oda_ref.get() # Initial data
    
    if oyuncu_sirasi == 'oyuncu1':
        oda_ref.update({
            'tahta': ['' for _ in range(9)],
            'sira': 'oyuncu1',
            'el_durumu': 'oynaniyor'
        })

    listener = oda_ref.listen(on_oda_degisti)
    
    sallanma_miktari = 0
    konfetiler = []
    
    el_sonu_zamani = 0
    el_beklemede = False
    
    mac_bitti = False
    mac_bitti_zamani = 0

    temp_surface = pygame.Surface((GENISLIK, YUKSEKLIK))
    
    while True:
        su_an = pygame.time.get_ticks()
        
        # Güvenlik kontrolü, oda_veri yoksa veya dictionary değilse odadan çık
        if not oda_veri or not isinstance(oda_veri, dict):
            break

        mevcut_tahta = oda_veri.get('tahta', ['' for _ in range(9)])
        mevcut_sira = oda_veri.get('sira', 'oyuncu1')
        el_durumu = oda_veri.get('el_durumu', 'oynaniyor')
        skor = oda_veri.get('skor', {'oyuncu1': 0, 'oyuncu2': 0})
        hedef_el = oda_veri.get('toplam_el', 3)
        hedef_skor = (hedef_el // 2) + 1
        
        # Kazanan kontrolü
        kazanan = check_win(mevcut_tahta)
        
        if kazanan and not el_beklemede and el_durumu == 'oynaniyor':
            el_beklemede = True
            el_sonu_zamani = su_an
            if oyuncu_sirasi == 'oyuncu1':
                yeni_skor_1 = skor.get('oyuncu1', 0) + (1 if kazanan == 'oyuncu1' else 0)
                yeni_skor_2 = skor.get('oyuncu2', 0) + (1 if kazanan == 'oyuncu2' else 0)
                oda_ref.update({
                    'el_durumu': 'bitti',
                    'kazanan': kazanan,
                    'skor': {'oyuncu1': yeni_skor_1, 'oyuncu2': yeni_skor_2}
                })
            
            if kazanan == oyuncu_sirasi:
                play_sound(ses_win)
                for _ in range(150):
                    konfetiler.append(Confetti(GENISLIK // 2, YUKSEKLIK))
            elif kazanan != 'draw':
                play_sound(ses_lose)
                sallanma_miktari = 20

        # El bitince 3 saniye bekle ve yeni ele veya maç sonuna geç
        if el_durumu == 'bitti' and su_an - el_sonu_zamani > 3000 and not mac_bitti:
            # Maçın bitip bitmediğini kontrol et
            if skor.get('oyuncu1', 0) >= hedef_skor or skor.get('oyuncu2', 0) >= hedef_skor:
                mac_bitti = True
                mac_bitti_zamani = su_an
                
                mac_kazanani = 'oyuncu1' if skor.get('oyuncu1', 0) >= hedef_skor else 'oyuncu2'
                
                # Global Leaderboard skoru güncelle
                if oyuncu_sirasi == mac_kazanani:
                    kullanici_ref = db.reference(f'kullanicilar/{kullanici_adi}')
                    user_data = kullanici_ref.get() or {}
                    eski_skor = user_data.get('skor', 0)
                    kullanici_ref.update({'skor': eski_skor + 1})
            else:
                if oyuncu_sirasi == 'oyuncu1':
                    mevcut_el = oda_veri.get('mevcut_el', 1)
                    oda_ref.update({
                        'tahta': ['' for _ in range(9)],
                        'sira': 'oyuncu1' if mevcut_el % 2 == 1 else 'oyuncu2',
                        'el_durumu': 'oynaniyor',
                        'kazanan': '',
                        'mevcut_el': mevcut_el + 1
                    })
                el_beklemede = False
                
        if mac_bitti and su_an - mac_bitti_zamani > 4000:
            if oyuncu_sirasi == 'oyuncu1':
                oda_ref.delete()
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if listener: close_listener_async(listener)
                if oyuncu_sirasi == 'oyuncu1': oda_ref.delete()
                else: oda_ref.child('oyuncular/oyuncu2').delete()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and mevcut_sira == oyuncu_sirasi and el_durumu == 'oynaniyor':
                pos = pygame.mouse.get_pos()
                # Geri butonuna tıklanma
                if 20 <= pos[0] <= 140 and 20 <= pos[1] <= 60:
                    break
                    
                # Ekran offsetini çıkararak tıklamayı hesapla
                col = (pos[0] - OFFSET_X) // KUTU_BOYUT
                row = (pos[1] - OFFSET_Y) // KUTU_BOYUT
                
                if 0 <= col < 3 and 0 <= row < 3:
                    index = row * 3 + col
                    if mevcut_tahta[index] == '':
                        mevcut_tahta[index] = oyuncu_sirasi
                        yeni_sira = 'oyuncu2' if oyuncu_sirasi == 'oyuncu1' else 'oyuncu1'
                        
                        if oyuncu_sirasi == 'oyuncu1': play_sound(ses_place_x)
                        else: play_sound(ses_place_o)
                        
                        oda_ref.update({
                            'tahta': mevcut_tahta,
                            'sira': yeni_sira
                        })

        # --- ÇİZİM İŞLEMLERİ ---
        temp_surface.fill((15, 15, 20))
        
        # Geri Dön Butonu
        pygame.draw.rect(temp_surface, (255, 80, 80), (20, 20, 120, 40), border_radius=8)
        btn_yazi = font_normal.render("Ayrıl", True, (255, 255, 255))
        temp_surface.blit(btn_yazi, btn_yazi.get_rect(center=(80, 40)))

        # Skor ve Bilgi Alanı
        p1_isim = oda_veri.get('oyuncular', {}).get('oyuncu1', 'Oyuncu 1')
        p2_isim = oda_veri.get('oyuncular', {}).get('oyuncu2', 'Oyuncu 2')
        skor_p1 = skor.get('oyuncu1', 0)
        skor_p2 = skor.get('oyuncu2', 0)
        
        skor_yazi = font_baslik.render(f"{p1_isim} (X)   {skor_p1} - {skor_p2}   {p2_isim} (O)", True, (255, 215, 0))
        temp_surface.blit(skor_yazi, skor_yazi.get_rect(center=(GENISLIK // 2, 50)))
        
        # Modern Tahta Çizimi (Neon glow effect simulation)
        for i in range(1, 3):
            # Dikey çizgiler
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y), (OFFSET_X + i * KUTU_BOYUT, OFFSET_Y + 3 * KUTU_BOYUT), 6)
            # Yatay çizgiler
            pygame.draw.line(temp_surface, (0, 150, 255), (OFFSET_X, OFFSET_Y + i * KUTU_BOYUT), (OFFSET_X + 3 * KUTU_BOYUT, OFFSET_Y + i * KUTU_BOYUT), 6)

        for idx, deger in enumerate(mevcut_tahta):
            x = OFFSET_X + (idx % 3) * KUTU_BOYUT + KUTU_BOYUT // 2
            y = OFFSET_Y + (idx // 3) * KUTU_BOYUT + KUTU_BOYUT // 2
            
            if deger == 'oyuncu1': # X - Neon Kırmızı
                pygame.draw.line(temp_surface, (255, 50, 50), (x-40, y-40), (x+40, y+40), 12)
                pygame.draw.line(temp_surface, (255, 50, 50), (x+40, y-40), (x-40, y+40), 12)
            elif deger == 'oyuncu2': # O - Neon Mavi
                pygame.draw.circle(temp_surface, (50, 200, 255), (x, y), 45, 10)

        # Durum Mesajı
        if mac_bitti:
            mac_kazanani = 'oyuncu1' if skor.get('oyuncu1', 0) >= hedef_skor else 'oyuncu2'
            durum_yazi = "MAÇI KAZANDIN!" if oyuncu_sirasi == mac_kazanani else "MAÇI KAYBETTİN!"
            renk = (50, 255, 50) if oyuncu_sirasi == mac_kazanani else (255, 50, 50)
        elif el_durumu == 'bitti':
            kaz = oda_veri.get('kazanan')
            if kaz == 'draw': durum_yazi, renk = "BERABERE!", (200, 200, 200)
            elif kaz == oyuncu_sirasi: durum_yazi, renk = "ELİ KAZANDIN!", (50, 255, 50)
            else: durum_yazi, renk = "ELİ KAYBETTİN!", (255, 50, 50)
        else:
            durum_yazi = "Sıra Sende!" if mevcut_sira == oyuncu_sirasi else "Rakibin Hamlesi Bekleniyor..."
            renk = (50, 255, 50) if mevcut_sira == oyuncu_sirasi else (200, 200, 200)
            
        bilgi = font_baslik.render(durum_yazi, True, renk)
        temp_surface.blit(bilgi, bilgi.get_rect(center=(GENISLIK // 2, YUKSEKLIK - 50)))

        # Konfetiler
        for k in konfetiler[:]:
            k.update()
            k.draw(temp_surface)
            if k.y > YUKSEKLIK:
                konfetiler.remove(k)

        # Sallanma (Screen Shake) hesapla ve çiz
        offset_x, offset_y = 0, 0
        if sallanma_miktari > 0:
            offset_x = random.randint(-sallanma_miktari, sallanma_miktari)
            offset_y = random.randint(-sallanma_miktari, sallanma_miktari)
            sallanma_miktari -= 1

        ekran.fill((0, 0, 0))
        ekran.blit(temp_surface, (offset_x, offset_y))
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)

    # Temizlik
    if listener:
        close_listener_async(listener)