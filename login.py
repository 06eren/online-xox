import pygame
import sys
import random
import firebase_admin
from firebase_admin import credentials, db

# Kendi yaptığımız menüyü projeye dahil ediyoruz
import menu 
import sesler
sesler.sesleri_hazirla()

# Pygame'i başlatıyoruz
pygame.init()
pygame.mixer.init()
try:
    ses_click = pygame.mixer.Sound("click.wav")
except:
    ses_click = None

def play_click():
    if ses_click: ses_click.play()

GENISLIK, YUKSEKLIK = 800, 600
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("Online XOX - Giriş")
saat = pygame.time.Clock()

# Kendi yaptığımız menüyü projeye dahil ediyoruz
import menu 

# --- FİREBASE BAĞLANTISI ---
try:
    cred = credentials.Certificate("anahtar.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://online-xox-a2421-default-rtdb.europe-west1.firebasedatabase.app/'
    })
except ValueError:
    pass 

# --- FONT VE RENKLER ---
try:
    font = pygame.font.Font("arial.ttf", 36)
    kucuk_font = pygame.font.Font("arial.ttf", 24)
except FileNotFoundError:
    font = pygame.font.Font(None, 36)
    kucuk_font = pygame.font.Font(None, 24)

KOYU_ARKAPLAN = (15, 15, 20)
KUTU_ARKAPLAN = (45, 45, 50)
KUTU_AKTIF = (60, 60, 70)
YAZI_RENGI = (220, 220, 220)
SILIK_YAZI = (120, 120, 120)
ANA_RENK = (0, 150, 255) 
ANA_RENK_HOVER = (50, 180, 255)
KIRMIZI = (255, 80, 80)
YESIL = (80, 255, 80)
SIYAH = (0, 0, 0)

# --- ANİMASYON (PARÇACIK SİSTEMİ) ---
class Parcacik:
    def __init__(self):
        self.x = random.randint(0, GENISLIK)
        self.y = random.randint(0, YUKSEKLIK)
        self.hiz_y = random.uniform(0.5, 2.0)
        self.boyut = random.randint(1, 4)
        self.renk = random.choice([(100, 100, 150), (50, 150, 255), (200, 200, 255)])

    def hareket_et(self):
        self.y -= self.hiz_y 
        if self.y < 0:
            self.y = YUKSEKLIK
            self.x = random.randint(0, GENISLIK)

    def ciz(self, ekran):
        pygame.draw.circle(ekran, self.renk, (self.x, int(self.y)), self.boyut)

parcaciklar = [Parcacik() for _ in range(70)]

# --- ARAYÜZ SINIFLARI ---
class TextBox:
    def __init__(self, x, y, genislik, yukseklik, placeholder, sifre_mi=False):
        self.rect = pygame.Rect(x, y, genislik, yukseklik)
        self.yazi = ''
        self.placeholder = placeholder
        self.aktif_mi = False
        self.sifre_mi = sifre_mi

    def ciz(self, ekran):
        renk = KUTU_AKTIF if self.aktif_mi else KUTU_ARKAPLAN
        cerceve_rengi = ANA_RENK if self.aktif_mi else SILIK_YAZI
        pygame.draw.rect(ekran, renk, self.rect, border_radius=10)
        pygame.draw.rect(ekran, cerceve_rengi, self.rect, 2, border_radius=10)
        gosterilecek_yazi = '*' * len(self.yazi) if self.sifre_mi and self.yazi else self.yazi
        if not self.yazi and not self.aktif_mi:
            yazi_yuzeyi = font.render(self.placeholder, True, SILIK_YAZI)
        else:
            yazi_yuzeyi = font.render(gosterilecek_yazi, True, YAZI_RENGI)
        yazi_rect = yazi_yuzeyi.get_rect(midleft=(self.rect.x + 15, self.rect.centery))
        ekran.blit(yazi_yuzeyi, yazi_rect)

class Button:
    def __init__(self, x, y, genislik, yukseklik, metin, ana_renk=ANA_RENK, hover_renk=ANA_RENK_HOVER):
        self.rect = pygame.Rect(x, y, genislik, yukseklik)
        self.metin = metin
        self.ana_renk = ana_renk
        self.hover_renk = hover_renk

    def ciz(self, ekran):
        fare_x, fare_y = pygame.mouse.get_pos()
        renk = self.hover_renk if self.rect.collidepoint((fare_x, fare_y)) else self.ana_renk
        pygame.draw.rect(ekran, renk, self.rect, border_radius=10)
        pygame.draw.rect(ekran, SIYAH, self.rect, 1, border_radius=10) 
        yazi_yuzeyi = font.render(self.metin, True, (255, 255, 255))
        yazi_rect = yazi_yuzeyi.get_rect(center=self.rect.center)
        ekran.blit(yazi_yuzeyi, yazi_rect)

    def tiklandi_mi(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                try: play_click()
                except: pass
                return True
        return False
# --- KUTULARI OLUŞTURMA ---
orta_x = GENISLIK // 2 - 150
login_kutular = [TextBox(orta_x, 200, 300, 45, "Kullanıcı Adı"), TextBox(orta_x, 260, 300, 45, "Şifre", True)]
btn_giris = Button(orta_x, 330, 300, 45, "Giriş Yap")
btn_kayda_git = Button(orta_x, 390, 300, 45, "Yeni Kayıt Ol", ANA_RENK, ANA_RENK_HOVER)

kayit_kutular = [TextBox(orta_x, 150, 300, 45, "Kullanıcı Adı"), TextBox(orta_x, 210, 300, 45, "E-Posta"), TextBox(orta_x, 270, 300, 45, "Şifre", True)]
btn_kayit_ol = Button(orta_x, 340, 300, 45, "Kaydı Tamamla")
btn_girise_don = Button(orta_x, 400, 300, 45, "Giriş Ekranına Dön", ANA_RENK, ANA_RENK_HOVER)

durum = "GIRIS" 
aktif_kutu_index = 0
mesaj = ""
mesaj_rengi = KIRMIZI

# --- FİREBASE İŞLEMLERİ ---
def formu_sifirla():
    global mesaj, aktif_kutu_index
    mesaj = ""
    aktif_kutu_index = 0
    for kutu in login_kutular + kayit_kutular:
        kutu.yazi = ""
        kutu.aktif_mi = False
    if durum == "GIRIS": login_kutular[0].aktif_mi = True
    elif durum == "KAYIT": kayit_kutular[0].aktif_mi = True

def kayit_iskenmi():
    global mesaj, durum, mesaj_rengi
    k, m, s = kayit_kutular[0].yazi, kayit_kutular[1].yazi, kayit_kutular[2].yazi
    if k == "" or m == "" or s == "":
        mesaj, mesaj_rengi = "Tüm alanları doldurun!", KIRMIZI
        return
    ref = db.reference(f'kullanicilar/{k}')
    if ref.get() is not None:
        mesaj, mesaj_rengi = "Bu kullanıcı adı alınmış!", KIRMIZI
    else:
        ref.set({'mail': m, 'sifre': s, 'skor': 0})
        mesaj, mesaj_rengi = "Kayıt başarılı! Giriş yapın.", YESIL
        durum = "GIRIS"
        formu_sifirla()

def giris_islemi():
    global mesaj, mesaj_rengi
    k, s = login_kutular[0].yazi, login_kutular[1].yazi
    if k == "" or s == "":
        mesaj, mesaj_rengi = "Bilgileri boş bırakmayın!", KIRMIZI
        return
    ref = db.reference(f'kullanicilar/{k}')
    kullanici_verisi = ref.get()
    
    if kullanici_verisi is not None and kullanici_verisi.get('sifre') == s:
        # GİRİŞ BAŞARILI, MENÜYE GEÇİŞ
        menu.goster(ekran, k) 
    else:
        mesaj, mesaj_rengi = "Kullanıcı adı veya şifre yanlış!", KIRMIZI

login_kutular[0].aktif_mi = True

# --- ANA DÖNGÜ ---
while True:
    ekran.fill(KOYU_ARKAPLAN)
    
    # Animasyon çizimi
    for p in parcaciklar:
        p.hareket_et()
        p.ciz(ekran)

    aktif_kutular = login_kutular if durum == "GIRIS" else kayit_kutular

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, kutu in enumerate(aktif_kutular):
                if kutu.rect.collidepoint(event.pos):
                    aktif_kutu_index = i
            
            if durum == "GIRIS":
                if btn_giris.tiklandi_mi(event): giris_islemi()
                elif btn_kayda_git.tiklandi_mi(event): 
                    durum = "KAYIT"
                    formu_sifirla()
            elif durum == "KAYIT":
                if btn_kayit_ol.tiklandi_mi(event): kayit_iskenmi()
                elif btn_girise_don.tiklandi_mi(event): 
                    durum = "GIRIS"
                    formu_sifirla()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                aktif_kutu_index = (aktif_kutu_index + 1) % len(aktif_kutular)
            elif event.key == pygame.K_RETURN:
                if durum == "GIRIS": giris_islemi()
                elif durum == "KAYIT": kayit_iskenmi()
            else:
                aktif_kutu = aktif_kutular[aktif_kutu_index]
                if event.key == pygame.K_BACKSPACE:
                    aktif_kutu.yazi = aktif_kutu.yazi[:-1]
                else:
                    aktif_kutu.yazi += event.unicode

    for i, kutu in enumerate(aktif_kutular):
        kutu.aktif_mi = (i == aktif_kutu_index)

    # Arayüz Elemanları (Animasyonun Üstüne Çizilir)
    baslik = font.render("ONLINE XOX", True, YAZI_RENGI)
    
    # Başlığa da estetik gölge ekleyelim
    golge = font.render("ONLINE XOX", True, SIYAH)
    baslik_x = GENISLIK // 2
    ekran.blit(golge, golge.get_rect(center=(baslik_x + 3, 83)))
    ekran.blit(baslik, baslik.get_rect(center=(baslik_x, 80)))

    if durum == "GIRIS":
        for kutu in login_kutular: kutu.ciz(ekran)
        btn_giris.ciz(ekran)
        btn_kayda_git.ciz(ekran)
    elif durum == "KAYIT":
        for kutu in kayit_kutular: kutu.ciz(ekran)
        btn_kayit_ol.ciz(ekran)
        btn_girise_don.ciz(ekran)

    if mesaj:
        mesaj_yuzeyi = kucuk_font.render(mesaj, True, mesaj_rengi)
        ekran.blit(mesaj_yuzeyi, mesaj_yuzeyi.get_rect(center=(GENISLIK//2, YUKSEKLIK - 50)))

    pygame.display.flip()
    saat.tick(60)