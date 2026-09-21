# Quiz

FastAPI + PostgreSQL ile yazılmış quiz uygulaması. Oyuncular kategori seçip soruları çözer, skorunu kaydeder ve
kategori bazlı skor tablosunu görür. Yönetici paneli ile kategori ve sorular yönetilir.

## Kurulum

```powershell
copy .env.example .env   # SECRET_KEY ve ADMIN_PASSWORD değerlerini doldur
```

`SECRET_KEY` için: `python -c "import secrets; print(secrets.token_hex(32))"`

## Docker ile çalıştırma (veritabanı + uygulama)

```powershell
docker compose up -d --build
docker compose run --rm app python -m app.seed   # örnek soruları ekler (istersen atla)
```

## Yerel geliştirme (uygulama Docker dışında)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
docker compose up -d db
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Docker'daki `app` servisi de 8000 portunu kullanır. Yerelde çalışmadan önce `docker compose stop app` ile durdur.

## Kullanıcılar

Yönetici kullanıcıları veritabanında (`users` tablosu) tutulur, şifreler argon2 ile hash'lenir.

- İlk açılışta `users` tablosu boşsa, `.env` içindeki `ADMIN_USERNAME` / `ADMIN_PASSWORD` ile ilk kullanıcı oluşturulur.
  Sonrasında `.env`'deki bu iki değer kullanılmaz. Şifreyi değiştirmek için API'yi kullan.
- `/docs` sayfasındaki **Authorize** iki yol sunar: kullanıcı adı ve şifreyle giriş (`OAuth2PasswordBearer`) ya da
  `POST /api/admin/login` cevabındaki `access_token`'ı yapıştırmak (`HTTPBearer`).
- Kullanıcıları `/docs` üzerinden (önce **Authorize** ile giriş yap) yönetebilirsin:
  `GET/POST /api/admin/users`, `GET/PUT/DELETE /api/admin/users/{id}`.
- `PUT` ile kullanıcı adı güncellenir. `password` alanı gönderilirse şifre de değişir, gönderilmezse aynı kalır.
- Son kalan kullanıcı silinemez. Silinen kullanıcının açık oturumu (token) hemen geçersiz olur.

## Arayüz

Arayüz düz HTML, CSS ve JavaScript'tir (framework ve derleme adımı yok) ve `app/static` klasöründen FastAPI ile sunulur.
Her şey `/api` altındaki endpoint'lere istek atar.

- `style.css`, `common.js`: iki sayfanın ortak stili ve yardımcı fonksiyonları
- `index.html`, `quiz.js`: quiz (kategori seç → soruları cevapla → skoru kaydet, skor tablosu)
- `admin/index.html`, `admin/admin.js`: yönetim paneli (kategoriler, sorular, kullanıcılar)

Docker'da çalışırken statik dosyalar imajın içine kopyalanır, değişiklikten sonra `docker compose up -d --build` gerekir.

## Adresler

| Adres | |
|---|---|
| http://localhost:8000/ | Quiz |
| http://localhost:8000/admin/ | Yönetici paneli (`.env` içindeki `ADMIN_USERNAME` / `ADMIN_PASSWORD`) |
| http://localhost:8000/docs | Swagger UI (endpoint'ler) |
| http://localhost:8000/redoc | ReDoc |

## Testler

Testler aynı Postgres sunucusunda ayrı bir `quiz_test` veritabanı kullanır (yoksa oluşturur), gerçek verilere dokunmaz.

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m pytest
```
