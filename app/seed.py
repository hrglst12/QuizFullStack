"""Idempotent starter data: python -m app.seed"""

from sqlalchemy import select

from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.models import Category, Question

# category -> [(question, options, index of the correct option)]
SEED = {
    "Ülkeler": [
        ("Avustralya'nın başkenti neresidir?", ["Sidney", "Canberra", "Melbourne", "Perth"], 1),
        ("Yüzölçümü bakımından en büyük ülke hangisidir?", ["Kanada", "Çin", "Rusya", "Amerika Birleşik Devletleri"], 2),
        ("Machu Picchu hangi ülkededir?", ["Peru", "Meksika", "Şili", "Bolivya"], 0),
    ],
    "Hayvanlar": [
        ("En büyük kara hayvanı hangisidir?", ["Zürafa", "Afrika fili", "Su aygırı", "Beyaz gergedan"], 1),
        ("Bir ahtapotun kaç kalbi vardır?", ["1", "2", "3", "4"], 2),
        ("Bu memelilerden hangisi gerçekten uçabilir?", ["Uçan sincap", "Yarasa", "Şeker sincabı", "Kolugo"], 1),
    ],
    "Programlama": [
        ("SQL kısaltması neyi ifade eder?", ["Structured Query Language", "Simple Question Language", "Sequential Query Logic", "Standard Queue Language"], 0),
        ("İkili aramanın (binary search) zaman karmaşıklığı nedir?", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1),
        ("Hangi HTTP durum kodu 'Not Found' (Bulunamadı) anlamına gelir?", ["200", "301", "404", "500"], 2),
    ],
    "Siber Güvenlik": [
        ("HTTPS'teki 'S' harfi hangi kelimeyi ifade eder?", ["Simple", "Secure", "Server", "Session"], 1),
        ("Kullanıcıları kimlik bilgilerini vermeye kandırmak için sahte mesajlar kullanan saldırı hangisidir?", ["Kimlik avı (phishing)", "Port tarama", "Kaba kuvvet (brute force)", "Tuş kaydı (keylogging)"], 0),
        ("Bunlardan hangisi bir kriptografik özet (hash) fonksiyonudur?", ["AES", "RSA", "SHA-256", "TLS"], 2),
    ],
}


def seed() -> None:
    with SessionLocal() as db:
        existing = set(db.scalars(select(Category.name)))
        for name, questions in SEED.items():
            if name not in existing:
                category = Category(name=name)
                db.add(category)
                db.flush()  # assigns category.id
                db.add_all(Question(category_id=category.id, text=t, options=o, answer_index=a) for t, o, a in questions)
        db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    seed()
