import requests
import csv
import json
import os

# Kullanıcıdan Gophish API URL ve API anahtarını alma
GOPHISH_URL = input("Gophish API URL'sini girin (örnek: https or http://192.168.1.1:3333): ")
API_KEY = input("Gophish API anahtarını girin (örnek: 4asd129d189f54aa6804400ae11312356e1ea6c05f51412assc2a6b271c): ")

def clean_for_csv(value):
    """CSV için string temizleme fonksiyonu"""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip().replace('"', '""').replace('\n', ' ').replace('\r', '').replace(';', ',')
    return value

# Kampanya ID'sini belirleyin
campaign_id = input("Rapor almak istediğiniz kampanya ID'sini girin: ")

# API'yi kullanarak kampanyadaki tüm verileri çekme
response = requests.get(
    f"{GOPHISH_URL}/api/campaigns/{campaign_id}/results",
    headers={"Authorization": f"Bearer {API_KEY}"},
    verify=False
)

# ... existing code ...

print(f"HTTP Status Code: {response.status_code}")

try:
    # Response'u JSON'a çevir
    campaign_data = response.json()
    
    # Timeline kısmını al
    timeline = campaign_data.get("timeline", [])
    print(f"\nToplam timeline kaydı: {len(timeline)}")
    
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

    print(f"Bulunan payload alanları: {', '.join(sorted(all_payload_keys))}")

    # Dinamik olarak payload anahtarlarından kolon adları oluştur
    payload_headers = [f"payload_{key}" for key in sorted(all_payload_keys)]

    # CSV dosyası yolunu oluşturma
    csv_filename = f"gophish_campaign_{campaign_id}_submitted_data.csv"
    csv_filepath = os.path.join(os.getcwd(), csv_filename)
    
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
                    
                    # Anahtar sayısı 2'den az olan payload'ları atla (bu sayede sadece rid yani kişiye özel oluşturulan anahtarı çekmesin diye böyle bir önlem eklendi)
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
                    print(f"Veri yazıldı: {entry.get('email')}")
                    
                except json.JSONDecodeError as e:
                    print(f"Details JSON parse hatası ({entry.get('email')}): {e}")
                    continue
                except Exception as e:
                    print(f"Beklenmeyen hata ({entry.get('email')}): {e}")
                    continue
                    
    print(f"\nİşlem tamamlandı:")
    print(f"Toplam kayıt: {len(timeline)}")
    print(f"Yazılan form gönderimi: {submitted_count}")
    print(f"CSV dosyası kaydedildi: {csv_filepath}")
    
except Exception as e:
    print(f"Hata oluştu: {e}")

