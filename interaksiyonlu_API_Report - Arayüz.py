import requests
import csv
import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading

def clean_for_csv(value):
    """CSV için string temizleme fonksiyonu"""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip().replace('"', '""').replace('\n', ' ').replace('\r', '').replace(';', ',')
    return value

def generate_report():
    # Arayüz elemanlarından değerleri al
    gophish_url = url_entry.get()
    api_key = api_key_entry.get()
    campaign_id = campaign_id_entry.get()
    
    # Girdi doğrulama
    if not gophish_url or not api_key or not campaign_id:
        messagebox.showerror("Hata", "Tüm alanları doldurunuz!")
        return
    
    # Butonları devre dışı bırak
    generate_button.config(state=tk.DISABLED)
    
    # Log alanını temizle
    log_area.config(state=tk.NORMAL)
    log_area.delete(1.0, tk.END)
    
    def process_report():
        try:
            log_area.insert(tk.END, "Rapor oluşturuluyor...\n")
            
            # API'yi kullanarak kampanyadaki tüm verileri çekme
            response = requests.get(
                f"{gophish_url}/api/campaigns/{campaign_id}/results",
                headers={"Authorization": f"Bearer {api_key}"},
                verify=False
            )
            
            log_area.insert(tk.END, f"HTTP Status Code: {response.status_code}\n")
            
            if response.status_code != 200:
                log_area.insert(tk.END, f"Hata: API yanıtı başarısız! (Kod: {response.status_code})\n")
                generate_button.config(state=tk.NORMAL)
                return
                
            # Response'u JSON'a çevir
            campaign_data = response.json()
            
            # Timeline kısmını al
            timeline = campaign_data.get("timeline", [])
            log_area.insert(tk.END, f"\nToplam timeline kaydı: {len(timeline)}\n")
            
            # Payload verilerini içeren anahtarları al (değer içerenleri)
            all_payload_keys = set()
            for entry in timeline:
                if entry.get("message") == "Submitted Data":
                    try:
                        details = json.loads(entry.get("details", "{}"))
                        payload = details.get("payload", {})
                        # Değer içeren payload anahtarlarını ekle
                        for key, value in payload.items():
                            if value:  # Boş değerleri ekleme
                                all_payload_keys.add(key)
                    except json.JSONDecodeError:
                        continue

            log_area.insert(tk.END, f"Bulunan payload alanları: {', '.join(sorted(all_payload_keys))}\n")

            # Dinamik olarak payload anahtarlarından kolon adları oluştur
            payload_headers = [f"payload_{key}" for key in sorted(all_payload_keys)]

            # CSV dosyası yolunu oluşturma
            csv_filename = f"gophish_campaign_{campaign_id}_submitted_data.csv"
            
            # Dosya kaydetme iletişim kutusu
            csv_filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Dosyaları", "*.csv")],
                initialfile=csv_filename
            )
            
            if not csv_filepath:
                log_area.insert(tk.END, "Dosya kaydetme iptal edildi.\n")
                generate_button.config(state=tk.NORMAL)
                return
            
            submitted_count = 0
            
            # Dosya oluşturma ve yazma
            with open(csv_filepath, mode="w", newline="", encoding="utf-8-sig") as file:  # BOM ekle
                writer = csv.writer(
                    file,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_NONNUMERIC,  # Sayısal olmayan değerleri tırnakla
                    escapechar='\\'
                )
                
                # Temel kolonlar + dinamik payload kolonları
                base_headers = [
                    "campaign_id",
                    "target_email",
                    "submission_time"
                ]
                
                # Tüm başlıkları yaz
                writer.writerow([clean_for_csv(header) for header in base_headers + payload_headers])
                
                # Her timeline kaydını kontrol et
                for entry in timeline:
                    if entry.get("message") == "Submitted Data":
                        try:
                            # Details string'ini JSON'a çevir
                            details = json.loads(entry.get("details", "{}"))
                            
                            # Payload'u al
                            payload = details.get("payload", {})
                            
                            # Anahtar sayısı 2'den az olan payload'ları atla
                            if len(payload) < 2:
                                continue
                            
                            # Temel verileri hazırla
                            base_data = [
                                entry.get("campaign_id", "N/A"),
                                clean_for_csv(entry.get("email", "N/A")),
                                clean_for_csv(entry.get("time", "N/A"))
                            ]
                            
                            # Payload verilerini hazırla
                            payload_data = []
                            for key in sorted(all_payload_keys):
                                value = payload.get(key, "")
                                payload_data.append(clean_for_csv(value))
                            
                            # Tüm veriyi yaz
                            writer.writerow(base_data + payload_data)
                            submitted_count += 1
                            log_area.insert(tk.END, f"Veri yazıldı: {entry.get('email')}\n")
                            
                        except json.JSONDecodeError as e:
                            log_area.insert(tk.END, f"Details JSON parse hatası ({entry.get('email')}): {e}\n")
                            continue
                        except Exception as e:
                            log_area.insert(tk.END, f"Beklenmeyen hata ({entry.get('email')}): {e}\n")
                            continue
                            
            log_area.insert(tk.END, f"\nİşlem tamamlandı:\n")
            log_area.insert(tk.END, f"Toplam kayıt: {len(timeline)}\n")
            log_area.insert(tk.END, f"Yazılan form gönderimi: {submitted_count}\n")
            log_area.insert(tk.END, f"CSV dosyası kaydedildi: {csv_filepath}\n")
            
            # Dosyayı açma seçeneği sun
            if messagebox.askyesno("Rapor Tamamlandı", "Oluşturulan CSV dosyasını açmak ister misiniz?"):
                os.startfile(csv_filepath)
                
        except requests.exceptions.RequestException as e:
            log_area.insert(tk.END, f"Bağlantı hatası: {e}\n")
        except Exception as e:
            log_area.insert(tk.END, f"Hata oluştu: {e}\n")
        finally:
            # İşlem tamamlandığında butonları aktif et
            generate_button.config(state=tk.NORMAL)
    
    # Rapor işlemini ayrı bir iş parçacığında çalıştır
    threading.Thread(target=process_report, daemon=True).start()

# Ana uygulama penceresi oluştur
root = tk.Tk()
root.title("Gophish CSV Rapor Oluşturucu")
root.geometry("700x600")
root.minsize(600, 500)

# Ana çerçeve
main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

# Başlık
title_label = ttk.Label(main_frame, text="Gophish Kampanya Bazlı Rapor Oluşturucu", font=("Arial", 14, "bold"))
title_label.pack(pady=(0, 20))

# Form çerçevesi
form_frame = ttk.LabelFrame(main_frame, text="Bağlantı Bilgileri", padding="10")
form_frame.pack(fill=tk.X, pady=(0, 10))

# Gophish URL
url_label = ttk.Label(form_frame, text="Gophish API URL:")
url_label.grid(row=0, column=0, sticky=tk.W, pady=5)
url_entry = ttk.Entry(form_frame, width=50)
url_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
url_entry.insert(0, "https://127.0.0.1:3333")  # Örnek değer

# API Key
api_key_label = ttk.Label(form_frame, text="API Anahtarı:")
api_key_label.grid(row=1, column=0, sticky=tk.W, pady=5)
api_key_entry = ttk.Entry(form_frame, width=50, show="*")
api_key_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
api_key_entry.insert(0, "4f54aa6804400ae63731asdea6c05f5a6957c6as4d2ak1smad2f2a6b271c")  # Örnek değer

# API Key göster/gizle
def toggle_api_key():
    if api_key_entry.cget('show') == '*':
        api_key_entry.config(show='')
        show_button.config(text='Gizle')
    else:
        api_key_entry.config(show='*')
        show_button.config(text='Göster')

show_button = ttk.Button(form_frame, text="Göster", width=8, command=toggle_api_key)
show_button.grid(row=1, column=2, padx=5, pady=5)

# Kampanya ID
campaign_id_label = ttk.Label(form_frame, text="Kampanya ID:")
campaign_id_label.grid(row=2, column=0, sticky=tk.W, pady=5)
campaign_id_entry = ttk.Entry(form_frame, width=50)
campaign_id_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

# Rapor oluşturma düğmesi
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)

generate_button = ttk.Button(button_frame, text="Rapor Oluştur", command=generate_report)
generate_button.pack(pady=10)

# Log alanı
log_frame = ttk.LabelFrame(main_frame, text="İşlem Logu", padding="10")
log_frame.pack(fill=tk.BOTH, expand=True)

log_area = scrolledtext.ScrolledText(log_frame, height=12)
log_area.pack(fill=tk.BOTH, expand=True)
log_area.config(state=tk.DISABLED)

# Altbilgi
footer_frame = ttk.Frame(main_frame)
footer_frame.pack(fill=tk.X, pady=(10, 0))

footer_label = ttk.Label(footer_frame, text="© 2025 Gophish Rapor Uygulaması By Furkan Yasin Keskin", font=("Arial", 8))
footer_label.pack(side=tk.RIGHT)

# Uygulamayı başlat
root.mainloop()