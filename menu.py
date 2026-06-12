import pygame
import sys
import random
import string
from firebase_admin import db
import game
import ai_bot
import sesler
import threading

def close_listener_async(listener):
    if listener:
        try:
            threading.Thread(target=listener.close, daemon=True).start()
        except:
            pass

try:
    pygame.mixer.init()
    ses_click = pygame.mixer.Sound("click.wav")
except:
    ses_click = None

ses_acik = True
def play_click():
    if ses_acik and ses_click:
        try: ses_click.play()
        except: pass

oda_guncel_veri = None
oda_listener = None
global_oda_kodu = None

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
    global oda_guncel_veri
    if event.event_type == 'put':
        if event.path == '/':
            oda_guncel_veri = event.data
        else:
            oda_guncel_veri = apply_update(oda_guncel_veri, event.path, event.data)
    elif event.event_type == 'patch':
        base_path = event.path if event.path != '/' else ''
        for rel_path, val in event.data.items():
            oda_guncel_veri = apply_update(oda_guncel_veri, f"{base_path}/{rel_path}", val)

class Parcacik:
    def __init__(self, genislik, yukseklik):
        self.x = random.randint(0, genislik)
        self.y = random.randint(0, yukseklik)
        self.hiz_y = random.uniform(0.5, 2.0)
        self.boyut = random.randint(1, 4)
        self.renk = random.choice([(100, 100, 150), (50, 150, 255), (200, 200, 255)])
        self.genislik = genislik
        self.yukseklik = yukseklik

    def hareket_et(self):
        self.y -= self.hiz_y 
        if self.y < 0:
            self.y = self.yukseklik
            self.x = random.randint(0, self.genislik)

    def ciz(self, elite_ekran):
        pygame.draw.circle(elite_ekran, self.renk, (self.x, int(self.y)), self.boyut)

class TextBox:
    def __init__(self, x, y, genislik, yukseklik, placeholder, font, sifre_mi=False, max_uzunluk=20):
        self.rect = pygame.Rect(x, y, genislik, yukseklik)
        self.yazi = ''
        self.placeholder = placeholder
        self.font = font
        self.aktif_mi = False
        self.sifre_mi = sifre_mi
        self.max_uzunluk = max_uzunluk

    def ciz(self, elite_ekran, aktif_renk, normal_renk, yazi_rengi, silik_renk):
        renk = aktif_renk if self.aktif_mi else normal_renk
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((renk[0], renk[1], renk[2], 180))
        elite_ekran.blit(s, (self.rect.x, self.rect.y))
        
        pygame.draw.rect(elite_ekran, aktif_renk if self.aktif_mi else silik_renk, self.rect, 2, border_radius=10)
        
        if not self.yazi:
            y_yuzey = self.font.render(self.placeholder, True, silik_renk)
        else:
            gosterilecek = '*' * len(self.yazi) if self.sifre_mi else self.yazi
            y_yuzey = self.font.render(gosterilecek, True, yazi_rengi)
        
        y_rect = y_yuzey.get_rect(midleft=(self.rect.x + 15, self.rect.centery))
        elite_ekran.blit(y_yuzey, y_rect)

class MenuButon:
    def __init__(self, x, y, genislik, yukseklik, metin, font, merkez_hizala=False):
        self.rect = pygame.Rect(x, y, genislik, yukseklik)
        if merkez_hizala:
            self.rect.x = x - genislik // 2
        self.metin = metin
        self.font = font
        self.hover = False

    def ciz(self, elite_ekran, ana_renk, hover_renk):
        fare_pos = pygame.mouse.get_pos()
        self.hover = self.rect.collidepoint(fare_pos)
        renk = hover_renk if self.hover else ana_renk
        
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((renk[0], renk[1], renk[2], 220))
        elite_ekran.blit(s, (self.rect.x, self.rect.y))
        pygame.draw.rect(elite_ekran, (0, 0, 0), self.rect, 1, border_radius=10)
        
        y_yuzey = self.font.render(self.metin, True, (255, 255, 255))
        y_rect = y_yuzey.get_rect(center=self.rect.center)
        elite_ekran.blit(y_yuzey, y_rect)

    def tiklandi_mi(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hover:
                play_click()
                return True
        return False

class OdaListesiOgesi:
    def __init__(self, x, y, genislik, yukseklik, kod, oda_verisi, font_m, font_k):
        self.rect = pygame.Rect(x, y, genislik, yukseklik)
        self.kod = kod
        self.oda_adi = oda_verisi.get('oda_adi', 'İsimsiz Oda')
        self.sifreli_mi = oda_verisi.get('sifreli_mi', False)
        self.masa_boyutu = oda_verisi.get('masa_boyutu', 3)
        self.oyuncu_sayisi = len(oda_verisi.get('oyuncular', {}))
        self.font_m = font_m
        self.font_k = font_k
        self.hover = False

    def ciz(self, ekran, aktif_renk, normal_renk):
        fare_pos = pygame.mouse.get_pos()
        self.hover = self.rect.collidepoint(fare_pos)
        renk = aktif_renk if self.hover else normal_renk
        
        pygame.draw.rect(ekran, renk, self.rect, border_radius=8)
        pygame.draw.rect(ekran, (0, 150, 255), self.rect, 1, border_radius=8)
        
        isim_metni = f"{self.oda_adi} {'(Sifreli)' if self.sifreli_mi else ''}"
        ekran.blit(self.font_m.render(isim_metni, True, (255, 255, 255)), (self.rect.x + 15, self.rect.y + 10))
        
        bilgi_metni = f"Kod: {self.kod}  |  {self.masa_boyutu}x{self.masa_boyutu}  |  {self.oyuncu_sayisi}/2 Oyuncu"
        ekran.blit(self.font_k.render(bilgi_metni, True, (150, 200, 255)), (self.rect.x + 15, self.rect.y + 45))

    def tiklandi_mi(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hover:
                play_click()
                return True
        return False

def ciz_avatar(ekran, x, y, avatar_id, boyut=40):
    if avatar_id == 1: # Mavi
        pygame.draw.circle(ekran, (50, 150, 255), (x, y), boyut//2)
    elif avatar_id == 2: # Kırmızı Ninja (Kare)
        pygame.draw.rect(ekran, (255, 50, 50), (x - boyut//2, y - boyut//2, boyut, boyut), border_radius=8)
    elif avatar_id == 3: # Yeşil Robot (Altıgen)
        pygame.draw.polygon(ekran, (50, 255, 50), [(x, y - boyut//2), (x + boyut//2, y - boyut//4), (x + boyut//2, y + boyut//4), (x, y + boyut//2), (x - boyut//2, y + boyut//4), (x - boyut//2, y - boyut//4)])
    elif avatar_id == 4: # Mor Üçgen
        pygame.draw.polygon(ekran, (200, 50, 255), [(x, y - boyut//2), (x + boyut//2, y + boyut//2), (x - boyut//2, y + boyut//2)])
    else: # Turuncu Oval
        pygame.draw.ellipse(ekran, (255, 150, 50), (x - boyut//2, y - boyut//3, boyut, boyut//1.5))

def goster(ekran, kullanici_adi):
    global oda_listener, oda_guncel_veri, ses_acik, global_oda_kodu
    GENISLIK, YUKSEKLIK = ekran.get_width(), ekran.get_height()
    saat = pygame.time.Clock()

    pygame.key.set_repeat(300, 50)

    font_isimleri = pygame.font.get_fonts()
    secili_font = "impact" if "impact" in font_isimleri else ("arialblack" if "arialblack" in font_isimleri else None)
    font_baslik = pygame.font.SysFont(secili_font, 50)
    font_m = pygame.font.SysFont(secili_font, 28)
    font_sm = pygame.font.SysFont(secili_font, 20) 
    font_k = pygame.font.SysFont(None, 24)

    KOYU_ARKAPLAN = (10, 10, 15)
    KUTU_ARKAPLAN = (40, 40, 45)
    KUTU_AKTIF = (55, 55, 65)
    ANA_RENK = (0, 150, 255)
    HOVER_RENK = (50, 200, 255)
    YESIL = (50, 220, 120)
    KIRMIZI = (255, 80, 80)
    ALTIN = (255, 215, 0)
    BEYAZ = (255, 255, 255)
    SILIK = (120, 120, 120)

    parcaciklar = [Parcacik(GENISLIK, YUKSEKLIK) for _ in range(80)]
    
    alt_durum = "ANA"
    mesaj = ""
    mesaj_rengi = KIRMIZI
    
    aktif_oda_kodu = ""
    oda_sahibi_mi = False
    toplam_el_secenekleri = [3, 5, 7, 10, 15, 20, 30, 50]
    el_index = 0
    masa_secenekleri = [3, 4, 5]
    masa_index = 0
    sifre_korumasi = False
    
    geri_sayim_basladi_mi = False
    geri_sayim_tetik_zamani = 0
    kalan_saniye = 3

    oda_listesi_ogeleri = []
    secilen_liste_odasi = None
    siralamalar = []

    orta_x = GENISLIK // 2
    
    # Kullanıcı verisini çek (Avatar vb.)
    user_ref = db.reference(f'kullanicilar/{kullanici_adi}').get() or {}
    secili_avatar = user_ref.get('avatar_id', 1)

    btn_ana = [
        MenuButon(orta_x, 180, 300, 45, "Oda Oluştur", font_m, True),
        MenuButon(orta_x, 240, 300, 45, "Odalara Göz At / Katıl", font_m, True),
        MenuButon(orta_x, 300, 300, 45, "Bota Karşı Oyna (AI)", font_m, True),
        MenuButon(orta_x, 360, 300, 45, "Sıralama", font_m, True),
        MenuButon(orta_x, 420, 300, 45, "Ayarlar", font_m, True),
        MenuButon(orta_x, 480, 300, 45, "Çıkış", font_m, True)
    ]
    
    # Oda Oluşturma
    txt_oda_adi = TextBox(orta_x - 150, 140, 300, 45, "Oda Adı", font_m)
    btn_sifre_toggle = MenuButon(orta_x, 200, 300, 45, "Şifre: KAPALI", font_m, True)
    txt_oda_sifre = TextBox(orta_x - 150, 260, 300, 45, "Oda Şifresi Girin", font_m, sifre_mi=True)
    
    btn_masa_azalt = MenuButon(orta_x - 150, 320, 50, 45, "-", font_m)
    btn_masa_arttir = MenuButon(orta_x + 100, 320, 50, 45, "+", font_m)
    
    btn_el_azalt = MenuButon(orta_x - 150, 380, 50, 45, "-", font_m)
    btn_el_arttir = MenuButon(orta_x + 100, 380, 50, 45, "+", font_m)
    
    btn_kur_tamamla = MenuButon(orta_x, 460, 300, 45, "Odayı Kur", font_m, True)
    btn_kur_geri = MenuButon(orta_x, 520, 300, 45, "Geri Dön", font_m, True)
    
    btn_katil_geri = MenuButon(20, 20, 120, 35, "Ana Menü", font_sm)
    btn_liste_yenile = MenuButon(GENISLIK - 140, 20, 120, 35, "Yenile", font_sm)
    txt_liste_sifre = TextBox(orta_x - 200, 390, 200, 40, "Oda Şifresi Girin", font_sm, sifre_mi=True)
    btn_liste_katil = MenuButon(orta_x + 20, 390, 180, 40, "Seçili Odaya Katıl", font_sm)
    txt_katil_kod = TextBox(orta_x - 260, 510, 140, 40, "Kod (4 Hane)", font_sm, max_uzunluk=4)
    txt_katil_sifre = TextBox(orta_x - 100, 510, 180, 40, "Şifre (Varsa)", font_sm, sifre_mi=True)
    btn_katil_onay = MenuButon(orta_x + 100, 510, 160, 40, "Manuel Bağlan", font_sm)

    btn_lobi_ayril = MenuButon(orta_x, 460, 200, 40, "Odadan Ayrıl", font_sm, True)

    btn_sir_geri = MenuButon(20, 20, 120, 35, "Ana Menü", font_sm)
    
    # Ayarlar
    btn_ayarlar_geri = MenuButon(20, 20, 120, 35, "Ana Menü", font_sm)
    btn_ses_toggle = MenuButon(orta_x, 150, 300, 45, "Sesler: AÇIK", font_m, True)
    txt_yeni_isim = TextBox(orta_x - 150, 220, 300, 45, "Yeni Kullanıcı Adı", font_m)
    btn_isim_degistir = MenuButon(orta_x, 280, 300, 45, "İsim Değiştir", font_m, True)
    btn_avatar_sol = MenuButon(orta_x - 100, 370, 40, 40, "<", font_m)
    btn_avatar_sag = MenuButon(orta_x + 60, 370, 40, 40, ">", font_m)
    btn_avatar_kaydet = MenuButon(orta_x, 450, 200, 40, "Avatarı Kaydet", font_m, True)

    btn_bot_kolay = MenuButon(orta_x, 200, 300, 45, "Kolay Bot", font_m, True)
    btn_bot_normal = MenuButon(orta_x, 260, 300, 45, "Normal Bot", font_m, True)
    btn_bot_zor = MenuButon(orta_x, 320, 300, 45, "Zor Bot", font_m, True)
    btn_bot_geri = MenuButon(orta_x, 380, 300, 45, "Ana Menü", font_m, True)

    create_kutular = [txt_oda_adi, txt_oda_sifre]
    join_kutular = [txt_katil_kod, txt_katil_sifre, txt_liste_sifre]
    ayar_kutular = [txt_yeni_isim]
    aktif_kutu_idx = 0

    txt_oda_adi.yazi = f"{kullanici_adi}'nin Odası"

    def siralama_getir():
        nonlocal siralamalar
        users = db.reference('kullanicilar').get() or {}
        liste = []
        for k, v in users.items():
            s = v.get('skor', 0)
            w = v.get('kazanma', 0)
            l = v.get('kaybetme', 0)
            a = v.get('avatar_id', 1)
            total = w + l
            rate = int((w / total * 100)) if total > 0 else 0
            liste.append((k, s, rate, a))
        siralamalar = sorted(liste, key=lambda x: x[1], reverse=True)[:10]

    def odalari_yenile():
        nonlocal oda_listesi_ogeleri, secilen_liste_odasi, mesaj
        oda_listesi_ogeleri.clear()
        secilen_liste_odasi = None
        tum_odalar = db.reference('odalar').get()
        baslangic_y = 100 
        eklenen = 0
        if tum_odalar:
            for kod, veri in tum_odalar.items():
                if veri.get('durum') == 'bekliyor' and len(veri.get('oyuncular', {})) < 2:
                    y_poz = baslangic_y + (eklenen * 85)
                    if eklenen < 3: 
                        oda_listesi_ogeleri.append(OdaListesiOgesi(orta_x - 250, y_poz, 500, 75, kod, veri, font_m, font_k))
                        eklenen += 1

    def odaya_baglanma_istegi(hedef_kod, girilen_sifre):
        nonlocal aktif_oda_kodu, oda_sahibi_mi, geri_sayim_basladi_mi, alt_durum, mesaj, mesaj_rengi
        global oda_listener, oda_guncel_veri, global_oda_kodu
        hedef_kod = hedef_kod.upper().strip()
        oda_kontrol = db.reference(f'odalar/{hedef_kod}').get()
        
        if not oda_kontrol:
            mesaj, mesaj_rengi = "Oda bulunamadı veya kapanmış!", KIRMIZI
        else:
            oyuncular = oda_kontrol.get('oyuncular', {})
            if 'oyuncu2' in oyuncular:
                mesaj, mesaj_rengi = "Bu oda dolmuş!", KIRMIZI
            elif oda_kontrol.get('durum') != 'bekliyor':
                mesaj, mesaj_rengi = "Bu odada oyun başlamış!", KIRMIZI
            elif oda_kontrol.get('sifreli_mi') and oda_kontrol.get('sifre') != girilen_sifre:
                mesaj, mesaj_rengi = "Hatalı oda şifresi!", KIRMIZI
            else:
                db.reference(f'odalar/{hedef_kod}/oyuncular').update({'oyuncu2': kullanici_adi})
                aktif_oda_kodu = hedef_kod
                global_oda_kodu = aktif_oda_kodu
                oda_sahibi_mi = False
                geri_sayim_basladi_mi = False
                alt_durum = "LOBBY"
                mesaj = ""
                oda_guncel_veri = oda_kontrol
                oda_listener = db.reference(f'odalar/{aktif_oda_kodu}').listen(on_oda_degisti)

    while True:
        su_an = pygame.time.get_ticks()
        ekran.fill(KOYU_ARKAPLAN)

        for p in parcaciklar:
            p.hareket_et()
            p.ciz(ekran)

        if alt_durum not in ["JOIN", "LOBBY", "SIRALAMA", "AYARLAR"]: 
            ekran.blit(font_k.render(f"Giriş Yapan: {kullanici_adi}", True, YESIL), (60, 20))
            ciz_avatar(ekran, 30, 30, secili_avatar, 30)

        if alt_durum == "LOBBY" and aktif_oda_kodu:
            if oda_guncel_veri is None:
                aktif_oda_kodu = ""
                geri_sayim_basladi_mi = False
                alt_durum = "ANA"
                mesaj, mesaj_rengi = "Oda sahibi odayı kapattı.", KIRMIZI
                if oda_listener:
                    close_listener_async(oda_listener)
                    oda_listener = None
            else:
                oyuncular = oda_guncel_veri.get('oyuncular', {})
                durum_db = oda_guncel_veri.get('durum', 'bekliyor')
                
                if 'oyuncu2' in oyuncular and not geri_sayim_basladi_mi:
                    geri_sayim_basladi_mi = True
                    geri_sayim_tetik_zamani = su_an
                    if oda_sahibi_mi:
                        db.reference(f'odalar/{aktif_oda_kodu}').update({'durum': 'gerisayim'})
                
                if 'oyuncu2' not in oyuncular and geri_sayim_basladi_mi:
                    geri_sayim_basladi_mi = False
                    if oda_sahibi_mi:
                        db.reference(f'odalar/{aktif_oda_kodu}').update({'durum': 'bekliyor'})

                if durum_db == 'oyun_basladi':
                    if oda_listener:
                        close_listener_async(oda_listener)
                        oda_listener = None
                    alt_durum = "XOX_BAŞLADI"

            if geri_sayim_basladi_mi:
                gecen = (su_an - geri_sayim_tetik_zamani) // 1000
                kalan_saniye = 3 - gecen
                if kalan_saniye <= 0:
                    kalan_saniye = 0
                    if oda_sahibi_mi:
                        db.reference(f'odalar/{aktif_oda_kodu}').update({'durum': 'oyun_basladi'})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if aktif_oda_kodu:
                    if oda_sahibi_mi: db.reference(f'odalar/{aktif_oda_kodu}').delete()
                    else: db.reference(f'odalar/{aktif_oda_kodu}/oyuncular/oyuncu2').delete()
                pygame.quit()
                sys.exit()

            current_boxes = create_kutular if alt_durum == "CREATE" else (join_kutular if alt_durum == "JOIN" else (ayar_kutular if alt_durum == "AYARLAR" else []))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for idx, box in enumerate(current_boxes):
                    if box.rect.collidepoint(event.pos):
                        aktif_kutu_idx = idx
            
            if event.type == pygame.KEYDOWN and current_boxes:
                if event.key == pygame.K_TAB:
                    aktif_kutu_idx = (aktif_kutu_idx + 1) % len(current_boxes)
                elif event.key == pygame.K_BACKSPACE:
                    current_boxes[aktif_kutu_idx].yazi = current_boxes[aktif_kutu_idx].yazi[:-1]
                elif event.key != pygame.K_RETURN:
                    if len(current_boxes[aktif_kutu_idx].yazi) < current_boxes[aktif_kutu_idx].max_uzunluk:
                        current_boxes[aktif_kutu_idx].yazi += event.unicode

            for idx, box in enumerate(current_boxes):
                box.aktif_mi = (idx == aktif_kutu_idx)

            if alt_durum == "ANA":
                if btn_ana[0].tiklandi_mi(event): 
                    alt_durum = "CREATE"
                    mesaj = ""
                elif btn_ana[1].tiklandi_mi(event): 
                    alt_durum = "JOIN"
                    mesaj = ""
                    odalari_yenile() 
                elif btn_ana[2].tiklandi_mi(event):
                    alt_durum = "BOT_SETUP"
                elif btn_ana[3].tiklandi_mi(event):
                    alt_durum = "SIRALAMA"
                    siralama_getir()
                elif btn_ana[4].tiklandi_mi(event):
                    alt_durum = "AYARLAR"
                elif btn_ana[5].tiklandi_mi(event):
                    pygame.quit()
                    sys.exit()
                    
            elif alt_durum == "AYARLAR":
                if btn_ayarlar_geri.tiklandi_mi(event): alt_durum = "ANA"
                elif btn_ses_toggle.tiklandi_mi(event):
                    ses_acik = not ses_acik
                    btn_ses_toggle.metin = "Sesler: AÇIK" if ses_acik else "Sesler: KAPALI"
                elif btn_isim_degistir.tiklandi_mi(event):
                    yeni_isim = txt_yeni_isim.yazi.strip()
                    if yeni_isim:
                        eski_ref = db.reference(f'kullanicilar/{kullanici_adi}').get()
                        if eski_ref:
                            if not db.reference(f'kullanicilar/{yeni_isim}').get():
                                db.reference(f'kullanicilar/{yeni_isim}').set(eski_ref)
                                db.reference(f'kullanicilar/{kullanici_adi}').delete()
                                kullanici_adi = yeni_isim
                                txt_oda_adi.yazi = f"{kullanici_adi}'nin Odası"
                                mesaj, mesaj_rengi = "İsim değiştirildi!", YESIL
                            else:
                                mesaj, mesaj_rengi = "Bu isim zaten alınmış!", KIRMIZI
                elif btn_avatar_sol.tiklandi_mi(event):
                    secili_avatar = secili_avatar - 1 if secili_avatar > 1 else 5
                elif btn_avatar_sag.tiklandi_mi(event):
                    secili_avatar = secili_avatar + 1 if secili_avatar < 5 else 1
                elif btn_avatar_kaydet.tiklandi_mi(event):
                    db.reference(f'kullanicilar/{kullanici_adi}').update({'avatar_id': secili_avatar})
                    mesaj, mesaj_rengi = "Avatar kaydedildi!", YESIL
                    
            elif alt_durum == "BOT_SETUP":
                if btn_bot_geri.tiklandi_mi(event): alt_durum = "ANA"
                elif btn_bot_kolay.tiklandi_mi(event):
                    ai_bot.botla_oyna(ekran, 3, 3, ses_acik, "kolay")
                    alt_durum = "ANA"
                elif btn_bot_normal.tiklandi_mi(event):
                    ai_bot.botla_oyna(ekran, 3, 3, ses_acik, "normal")
                    alt_durum = "ANA"
                elif btn_bot_zor.tiklandi_mi(event):
                    ai_bot.botla_oyna(ekran, 3, 3, ses_acik, "zor")
                    alt_durum = "ANA"

            elif alt_durum == "SIRALAMA":
                if btn_sir_geri.tiklandi_mi(event): alt_durum = "ANA"

            elif alt_durum == "CREATE":
                if btn_kur_geri.tiklandi_mi(event): alt_durum = "ANA"
                elif btn_sifre_toggle.tiklandi_mi(event):
                    sifre_korumasi = not sifre_korumasi
                    btn_sifre_toggle.metin = "Şifre: AÇIK" if sifre_korumasi else "Şifre: KAPALI"
                elif btn_masa_azalt.tiklandi_mi(event):
                    masa_index = (masa_index - 1) % len(masa_secenekleri)
                elif btn_masa_arttir.tiklandi_mi(event):
                    masa_index = (masa_index + 1) % len(masa_secenekleri)
                elif btn_el_azalt.tiklandi_mi(event):
                    el_index = (el_index - 1) % len(toplam_el_secenekleri)
                elif btn_el_arttir.tiklandi_mi(event):
                    el_index = (el_index + 1) % len(toplam_el_secenekleri)
                elif btn_kur_tamamla.tiklandi_mi(event):
                    if txt_oda_adi.yazi.strip() == "":
                        mesaj, mesaj_rengi = "Oda adı boş olamaz!", KIRMIZI
                    elif sifre_mi := (sifre_korumasi and txt_oda_sifre.yazi.strip() == ""):
                        mesaj, mesaj_rengi = "Lütfen şifre belirleyin!", KIRMIZI
                    else:
                        aktif_oda_kodu = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                        oda_verisi = {
                            'oda_adi': txt_oda_adi.yazi,
                            'sifreli_mi': sifre_korumasi,
                            'sifre': txt_oda_sifre.yazi if sifre_korumasi else '',
                            'toplam_el': toplam_el_secenekleri[el_index],
                            'masa_boyutu': masa_secenekleri[masa_index],
                            'durum': 'bekliyor',
                            'oyuncular': {'oyuncu1': kullanici_adi},
                            'skor': {'oyuncu1': 0, 'oyuncu2': 0},
                            'mevcut_el': 1,
                            'chat': []
                        }
                        db.reference(f'odalar/{aktif_oda_kodu}').set(oda_verisi)
                        oda_sahibi_mi = True
                        geri_sayim_basladi_mi = False
                        alt_durum = "LOBBY"
                        global_oda_kodu = aktif_oda_kodu
                        btn_lobi_ayril.metin = "Odayı Kapat"
                        mesaj = ""
                        oda_guncel_veri = oda_verisi
                        oda_listener = db.reference(f'odalar/{aktif_oda_kodu}').listen(on_oda_degisti)

            elif alt_durum == "JOIN":
                if btn_katil_geri.tiklandi_mi(event): alt_durum = "ANA"
                elif btn_liste_yenile.tiklandi_mi(event): odalari_yenile()
                
                elif btn_katil_onay.tiklandi_mi(event):
                    if txt_katil_kod.yazi.strip() == "":
                        mesaj, mesaj_rengi = "Lütfen 4 haneli kodu girin!", KIRMIZI
                    else:
                        odaya_baglanma_istegi(txt_katil_kod.yazi, txt_katil_sifre.yazi)
                
                for oda_ogesi in oda_listesi_ogeleri:
                    if oda_ogesi.tiklandi_mi(event):
                        secilen_liste_odasi = oda_ogesi
                        txt_liste_sifre.yazi = "" 
                        
                        if not secilen_liste_odasi.sifreli_mi:
                            odaya_baglanma_istegi(secilen_liste_odasi.kod, "")
                
                if secilen_liste_odasi and secilen_liste_odasi.sifreli_mi:
                    if btn_liste_katil.tiklandi_mi(event):
                        odaya_baglanma_istegi(secilen_liste_odasi.kod, txt_liste_sifre.yazi)

            elif alt_durum == "LOBBY":
                if btn_lobi_ayril.tiklandi_mi(event):
                    if oda_listener:
                        close_listener_async(oda_listener)
                        oda_listener = None
                    if oda_sahibi_mi:
                        db.reference(f'odalar/{aktif_oda_kodu}').delete()
                        mesaj, mesaj_rengi = "Odayı başarıyla kapattınız.", YESIL
                    else:
                        db.reference(f'odalar/{aktif_oda_kodu}/oyuncular/oyuncu2').delete()
                        db.reference(f'odalar/{aktif_oda_kodu}').update({'durum': 'bekliyor'})
                        mesaj, mesaj_rengi = "Odadan ayrıldınız.", YESIL
                    aktif_oda_kodu = ""
                    geri_sayim_basladi_mi = False
                    alt_durum = "ANA"

        if alt_durum == "ANA":
            baslik = font_baslik.render("XOX ANA MENÜ", True, ANA_RENK)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 90)))
            for btn in btn_ana: btn.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)

        elif alt_durum == "BOT_SETUP":
            baslik = font_baslik.render("ZORLUK SEÇ", True, ANA_RENK)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 90)))
            btn_bot_kolay.ciz(ekran, KUTU_ARKAPLAN, YESIL)
            btn_bot_normal.ciz(ekran, KUTU_ARKAPLAN, ALTIN)
            btn_bot_zor.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)
            btn_bot_geri.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)

        elif alt_durum == "AYARLAR":
            baslik = font_baslik.render("AYARLAR", True, ANA_RENK)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 80)))
            btn_ayarlar_geri.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)
            btn_ses_toggle.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            txt_yeni_isim.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
            btn_isim_degistir.ciz(ekran, KUTU_ARKAPLAN, YESIL)
            
            ekran.blit(font_m.render("Profil Avatarı", True, BEYAZ), (orta_x - 70, 330))
            btn_avatar_sol.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            ciz_avatar(ekran, orta_x, 390, secili_avatar, 50)
            btn_avatar_sag.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            btn_avatar_kaydet.ciz(ekran, KUTU_ARKAPLAN, YESIL)

        elif alt_durum == "SIRALAMA":
            baslik = font_baslik.render("LİDERLİK TABLOSU", True, ALTIN)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 60)))
            btn_sir_geri.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)
            
            y_offset = 120
            for i, (isim, skor, wr, av_id) in enumerate(siralamalar):
                renk = ALTIN if i == 0 else (192, 192, 192) if i == 1 else (205, 127, 50) if i == 2 else BEYAZ
                ciz_avatar(ekran, orta_x - 200, y_offset + 10, av_id, 30)
                metin = font_m.render(f"{i+1}. {isim} | Skor: {skor} | WR: %{wr}", True, renk)
                ekran.blit(metin, metin.get_rect(midleft=(orta_x - 170, y_offset + 10)))
                y_offset += 40

        elif alt_durum == "CREATE":
            baslik = font_baslik.render("ODA OLUŞTUR", True, ANA_RENK)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 60)))
            
            txt_oda_adi.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
            btn_sifre_toggle.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            if sifre_korumasi:
                txt_oda_sifre.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
            
            btn_masa_azalt.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            m_metni = font_m.render(f"Masa: {masa_secenekleri[masa_index]}x{masa_secenekleri[masa_index]}", True, BEYAZ)
            ekran.blit(m_metni, m_metni.get_rect(center=(orta_x, 342)))
            btn_masa_arttir.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)

            btn_el_azalt.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            el_metni = font_m.render(f"El Sayısı: {toplam_el_secenekleri[el_index]}", True, BEYAZ)
            ekran.blit(el_metni, el_metni.get_rect(center=(orta_x, 402)))
            btn_el_arttir.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            
            btn_kur_tamamla.ciz(ekran, KUTU_ARKAPLAN, YESIL)
            btn_kur_geri.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)

        elif alt_durum == "JOIN":
            baslik = font_baslik.render("ODALAR", True, ANA_RENK)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 40)))
            
            btn_katil_geri.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)
            btn_liste_yenile.ciz(ekran, KUTU_ARKAPLAN, HOVER_RENK)
            
            if not oda_listesi_ogeleri:
                bilgi = font_k.render("Açık ve bekleyen oda bulunamadı.", True, SILIK)
                ekran.blit(bilgi, bilgi.get_rect(center=(orta_x, 200)))
            else:
                for oda_ogesi in oda_listesi_ogeleri:
                    aktif_renk = (70, 100, 70) if secilen_liste_odasi == oda_ogesi else KUTU_AKTIF
                    oda_ogesi.ciz(ekran, aktif_renk, KUTU_ARKAPLAN)

            if secilen_liste_odasi and secilen_liste_odasi.sifreli_mi:
                txt_liste_sifre.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
                btn_liste_katil.ciz(ekran, KUTU_ARKAPLAN, YESIL)

            pygame.draw.line(ekran, SILIK, (50, 470), (GENISLIK - 50, 470), 1)
            bilgi_manuel = font_k.render("Manuel Olarak Bir Odaya Katıl", True, SILIK)
            ekran.blit(bilgi_manuel, bilgi_manuel.get_rect(center=(orta_x, 485)))
            
            txt_katil_kod.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
            txt_katil_sifre.ciz(ekran, KUTU_AKTIF, KUTU_ARKAPLAN, BEYAZ, SILIK)
            btn_katil_onay.ciz(ekran, KUTU_ARKAPLAN, ANA_RENK)

        elif alt_durum == "LOBBY":
            baslik = font_baslik.render("OYUN LOBİSİ", True, YESIL)
            ekran.blit(baslik, baslik.get_rect(center=(orta_x, 70)))
            
            if oda_guncel_veri:
                p1 = oda_guncel_veri.get('oyuncular', {}).get('oyuncu1', 'Bağlanıyor...')
                p2 = oda_guncel_veri.get('oyuncular', {}).get('oyuncu2', 'Rakip Bekleniyor...')
                el_sayisi = oda_guncel_veri.get('toplam_el', 3)
                m_boyut = oda_guncel_veri.get('masa_boyutu', 3)
                
                pygame.draw.rect(ekran, KUTU_ARKAPLAN, (orta_x - 220, 120, 440, 310), border_radius=15)
                
                ekran.blit(font_m.render(f"Oda: {oda_guncel_veri.get('oda_adi')}", True, ANA_RENK), (orta_x - 190, 140))
                ekran.blit(font_m.render(f"Kod: {aktif_oda_kodu}", True, YESIL), (orta_x - 190, 180))
                ekran.blit(font_m.render(f"Masa: {m_boyut}x{m_boyut}", True, BEYAZ), (orta_x - 190, 220))
                ekran.blit(font_m.render(f"Hedef Tur: {el_sayisi} El", True, BEYAZ), (orta_x - 190, 260))
                
                pygame.draw.line(ekran, SILIK, (orta_x - 190, 300), (orta_x + 190, 300), 1)
                
                ekran.blit(font_m.render(f"1. Oyuncu (X): {p1}", True, BEYAZ), (orta_x - 190, 320))
                ekran.blit(font_m.render(f"2. Oyuncu (O): {p2}", True, BEYAZ if p2 != 'Rakip Bekleniyor...' else SILIK), (orta_x - 190, 360))
                
                if not geri_sayim_basladi_mi:
                    btn_lobi_ayril.ciz(ekran, KUTU_ARKAPLAN, KIRMIZI)

                if geri_sayim_basladi_mi:
                    sayac_yuzey = font_baslik.render(str(kalan_saniye), True, KIRMIZI)
                    ekran.blit(sayac_yuzey, sayac_yuzey.get_rect(center=(orta_x, 480)))
                    bilgi_yuzey = font_m.render("Maç Başlıyor...", True, BEYAZ)
                    ekran.blit(bilgi_yuzey, bilgi_yuzey.get_rect(center=(orta_x, 540)))
                else:
                    bilgi_yuzey = font_k.render("Arkadaşınıza kodu verin veya listeden katılmasını bekleyin.", True, SILIK)
                    ekran.blit(bilgi_yuzey, bilgi_yuzey.get_rect(center=(orta_x, 520)))

        elif alt_durum == "XOX_BAŞLADI":
            ekran.fill(KOYU_ARKAPLAN)
            mac_yazi = font_baslik.render("TAHTA YÜKLENİYOR...", True, ANA_RENK)
            ekran.blit(mac_yazi, mac_yazi.get_rect(center=(orta_x, YUKSEKLIK // 2)))
            pygame.display.flip()
            pygame.time.delay(500)
            
            oda_verisi = db.reference(f'odalar/{aktif_oda_kodu}').get()
            benim_siram = 'oyuncu1' if oda_verisi['oyuncular']['oyuncu1'] == kullanici_adi else 'oyuncu2'
            game.oyunu_baslat(ekran, kullanici_adi, aktif_oda_kodu, benim_siram, ses_acik)
            alt_durum = "ANA"

        if mesaj and not (alt_durum == "LOBBY" and geri_sayim_basladi_mi):
            mesaj_yuzeyi = font_k.render(mesaj, True, mesaj_rengi)
            ekran.blit(mesaj_yuzeyi, mesaj_yuzeyi.get_rect(center=(orta_x, YUKSEKLIK - 30)))

        # Watermark
        watermark = font_k.render("Developed By: ERN YAZILIM", True, (100, 100, 100))
        ekran.blit(watermark, (GENISLIK - watermark.get_width() - 10, YUKSEKLIK - watermark.get_height() - 10))

        pygame.display.flip()
        saat.tick(60)