# Lucky Spin Bot

Dokumen ini menjelaskan alur kerja bot Telegram pada project ini, termasuk perilaku bot di chat grup, chat pribadi, dan integrasi dengan Google Apps Script serta Google Sheets.

## Ringkasan Fungsi Bot

Bot ini dipakai untuk membantu member mengambil kode akses Lucky Spin, masuk ke halaman spin, lalu mengajukan klaim hadiah lewat private chat.

Alur utama dibagi menjadi 2 tempat:

- Chat grup: bot menampilkan menu utama, menyambut member baru, dan mengarahkan member ke chat pribadi untuk ambil kode akses.
- Chat pribadi: bot meminta `User ID`, mengecek data ke Google Sheets melalui Apps Script, lalu memberikan kode akses jika `User ID` dan `TELE ID` belum klaim hari itu. Setelah spin selesai, bot juga bisa membaca screenshot hasil spin atau menanggapi teks user terkait hadiah lalu meneruskan klaim ke admin.

## File Penting

- [bot.py](c:/Users/Bot-telegram/bot.py)
  File utama bot Telegram.
- [G-Apps.js](c:/Users/Bot-telegram/G-Apps.js)
  Script Google Apps Script untuk koneksi ke Google Sheets.
- [.env](c:/Users/Bot-telegram/.env)
  Menyimpan `BOT_TOKEN` dan `GOOGLE_SCRIPT_URL`.
- [lucky_spin_usage.json](c:/Users/Bot-telegram/lucky_spin_usage.json)
  Penyimpanan lokal cooldown kode untuk validasi lokal yang masih tersisa di bot.
- [lucky_spin_assignments.json](c:/Users/Bot-telegram/lucky_spin_assignments.json)
  File lama dari sistem assignment lokal. Saat ini tidak lagi dipakai oleh flow ambil kode dari Google Sheets.
- [pending_admin_claims.json](c:/Users/Bot-telegram/pending_admin_claims.json)
  Menyimpan daftar klaim hadiah yang sudah diteruskan ke admin dan menunggu balasan `Done`.
- [private_claim_statuses.json](c:/Users/Bot-telegram/private_claim_statuses.json)
  Menyimpan status klaim private per member agar status `validated`, `awaiting_admin`, dan `completed` tetap ada walau bot restart.
- [private_chat_logs.json](c:/Users/Bot-telegram/private_chat_logs.json)
  Menyimpan log percakapan private member dan balasan bot untuk kebutuhan dashboard admin.

## Konfigurasi Environment

Isi `.env` minimal:

```env
BOT_TOKEN=token_bot_telegram
GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/.../exec
```

Untuk fitur baca screenshot hasil Lucky Spin di private chat, tambahkan juga:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Keterangan:

- `BOT_TOKEN`: token bot Telegram dari BotFather.
- `GOOGLE_SCRIPT_URL`: URL Web App Apps Script yang berakhiran `/exec`.
- `TESSERACT_CMD`: opsional untuk Windows jika `tesseract.exe` belum masuk PATH. Di Railway biasanya tidak perlu jika package `tesseract` sudah tersedia di image deploy.

Dashboard admin membaca identitas admin dari:

- `ADMIN_USERNAME`
- `ADMIN_CHAT_ID`
- `DASHBOARD_HOST`
- `DASHBOARD_PORT`
- `DASHBOARD_PUBLIC_URL`
- `DASHBOARD_TOKEN`

Jika `ADMIN_CHAT_ID` belum diisi, bot tetap bisa mengenali admin dari username sesuai `ADMIN_USERNAME`.

Untuk dashboard web terpisah:

- `DASHBOARD_HOST`: default `0.0.0.0`
- `DASHBOARD_PORT`: default `8080` atau mengikuti `PORT`
- `DASHBOARD_PUBLIC_URL`: URL publik yang akan dibagikan ke admin, misalnya `https://dashboard.domainkamu.com`
- `DASHBOARD_TOKEN`: token akses dashboard web. Sangat disarankan diisi kalau dashboard dibuka ke internet.

## Alur Bot di Chat Grup

### 1. Sambutan Member Baru

Saat ada member baru masuk grup, bot mengirim pesan:

```text
Halo {name} Selamat Bergabung di Group Horeg22 Official, semoga nyaman yaa !! Ada Bonus Lucky Spin nih, Yuk ambil sekarang !!
```

Lalu bot menampilkan menu grup.

### 2. Menu yang Tampil di Grup

Menu grup saat ini berisi:

- `Klaim Lucky Spin`
- `Ambil Kode Akses`
- `Login`
- `Daftar`
- `Buka Halaman Lucky Spin`

### 3. Fungsi Tiap Menu di Grup

#### `Klaim Lucky Spin`

Saat tombol ini diklik, bot tidak memulai input `User ID` atau `Kode Akses`.

Bot hanya membalas:

```text
Lucky Spin dapat Di klaim 1 kali dalam 1 hari, Jika kamu belum ada Klaim Lucky Spin nya langsung klik menu Ambil kode akses ya !
```

Lalu bot menampilkan kembali menu grup.

Tujuan tombol ini sekarang hanya sebagai pengarah ke tombol `Ambil Kode Akses`.

#### `Ambil Kode Akses`

Tombol ini membuka chat pribadi ke bot memakai deep link:

```text
https://t.me/<username_bot>?start=getkode
```

Tujuannya supaya pengambilan kode dilakukan di private chat, bukan di grup.

#### `Login`

Mengarah ke:

```text
https://www.horeg22.net/login
```

#### `Daftar`

Mengarah ke:

```text
https://www.horeg22.net/register
```

#### `Buka Halaman Lucky Spin`

Mengarah ke:

```text
https://lckyspn.netlify.app/
```

### 4. Respon Keyword di Grup

Bot juga memiliki auto reply untuk beberapa kata kunci pada pesan teks biasa.

Keyword yang dipantau:

- `luckyspin`
- `lucky spin`
- `klaim spin`
- `klaim luckyspin`
- `kode akses`

Respon umumnya:

- Jika pesan mengandung `spin` atau `klaim`, bot mengarahkan user untuk ketik `/spin`.
- Jika pesan mengandung `kode`, bot mengarahkan user untuk klik `Ambil Kode Akses`.
- Jika pesan mengandung `login`, bot membalas link login.
- Jika pesan mengandung `daftar` atau `register`, bot membalas link daftar.

### 5. Anti Spam Link di Grup

Bot mencoba menghapus pesan yang mengandung link selain domain berikut:

- `lckyspn.netlify.app`
- `horeg22.net`

## Dashboard Admin

Bot sekarang punya dashboard internal yang hanya bisa diakses admin lewat private chat bot.

Command:

```text
/dashboard
```

Command dashboard web:

```text
/dashboardweb
```

Fungsi dashboard:

- melihat daftar chat private member yang terekam
- melihat update terakhir tiap member
- membuka detail percakapan per member lewat tombol inline
- melihat pesan masuk member dan balasan bot pada flow private chat
- mencari log berdasarkan `chat_id`, `username`, `user_id`, nama member, dan potongan isi chat
- export log ke file `JSON` atau `CSV`

Keamanan akses:

- hanya akun yang cocok dengan `ADMIN_USERNAME` atau `ADMIN_CHAT_ID` yang bisa membuka dashboard
- akun owner `@trustno_one9` juga bisa membuka dashboard
- chat admin tidak disimpan sebagai chat member di file log
- jika `DASHBOARD_TOKEN` diisi, dashboard web hanya bisa dibuka dengan token tersebut

## Alur Bot di Chat Pribadi

### 1. Saat User Masuk ke Bot

Jika user masuk ke bot lewat:

- tombol `Ambil Kode Akses` dari grup, atau
- mengetik `/start` di private chat, atau
- mengirim teks `kode akses` di private chat,

maka bot akan masuk ke flow pengambilan kode.

Bot membalas:

```text
Di bantu berikan User ID-nya ya bosku.
Contoh User ID: User1234
```

atau pada `/start` private biasa:

```text
Halo, saya Taro Admin.

Kirim User ID kamu untuk ambil kode akses Lucky Spin.
Contoh User ID: User1234
```

Setelah itu bot menunggu input `User ID`.

### 2. Saat User Mengirim User ID

Bot melakukan proses berikut:

1. membaca pesan sebagai `User ID`
2. validasi minimal 3 karakter
3. mengirim request ke Google Apps Script

Payload yang dikirim:

```json
{
  "action": "claim_code",
  "user_id": "User1234",
  "tele_id": "123456789"
}
```

### 3. Jika User ID dan Tele ID Belum Pernah Klaim

Jika Apps Script mengembalikan status sukses, bot membalas:

```text
Kode akses Lucky Spin kamu:

KODE

Simpan kode akses kamu dan lanjutkan pilih menu di bawah ini untuk melanjutkan memutar Lucky Spin nya.
```

Lalu bot menampilkan menu private.

### 4. Menu yang Tampil di Private Chat

Menu private saat ini berisi:

- `Buka Halaman Lucky Spin`
- `Panduan Lucky Spin`

#### `Buka Halaman Lucky Spin`

Mengarah ke:

```text
https://lckyspn.netlify.app/
```

#### `Panduan Lucky Spin`

Saat diklik di private chat, bot:

- mengirim gambar dari file `images/panduan.jpg` jika file tersedia
- menambahkan caption panduan
- menampilkan menu private lagi

### 5. Respon Cerdas di Private Chat

Setelah user lolos validasi dan sudah mendapatkan kode akses, bot menyimpan `validated_user_id` di session private chat.

Setelah itu, bot private sekarang tidak hanya menunggu screenshot atau nominal hadiah, tetapi juga membaca maksud chat member dan memberi respons sesuai konteks session.

Intent yang sekarang dikenali antara lain:

- `ambil kode`, `minta kode`, `kode akses`, `kode saya`
- `panduan`, `tutorial`, `cara spin`, `cara main`, `gimana spin`
- `login`, `link login`
- `daftar`, `register`, `link daftar`
- `link spin`, `halaman spin`, `buka spin`
- `sudah spin`, `mau klaim`, `klaim hadiah`
- `status klaim`, `sudah belum`, `diproses`, `proses admin`
- `admin`, `hubungi admin`, `cs`
- sapaan umum seperti `halo`, `menu`, `help`, `tolong`

Bot juga dibuat lebih toleran terhadap typo ringan seperti `kode aces`, `kode akes`, atau variasi penulisan member yang tidak rapi.

Logika session-aware yang sekarang dipakai:

- jika member belum pernah validasi `User ID`, bot akan mengarahkan ke flow ambil kode
- jika member sudah dapat kode, bot akan mengarahkan untuk buka Lucky Spin dan kirim hasil spin
- jika klaim sudah diteruskan ke admin, bot bisa menjawab status klaim
- jika admin sudah menandai klaim selesai, bot akan menyimpan status selesai untuk chat member itu

Bot juga punya anti-spam ringan khusus private chat:

- jika member mengirim pesan yang sama berulang kali dalam waktu singkat, bot hanya mengirim satu balasan pengarah
- tujuannya supaya chat tidak loop dan member tetap diarahkan ke langkah berikutnya

Selain itu, setelah kode akses berhasil diberikan, bot sekarang langsung mengirim follow-up tambahan agar member tahu bahwa langkah berikutnya adalah kirim screenshot hasil spin atau nominal hadiah jika lupa screenshot.

### 6. Klaim Hadiah di Private Chat

Sesudah validasi berhasil, ada 2 jalur klaim yang bisa dipakai user:

#### A. Klaim lewat screenshot

Jika user mengirim screenshot hasil Lucky Spin ke bot di private chat, bot akan:

1. mengambil foto dari Telegram
2. menjalankan OCR lokal dengan `pytesseract`
3. mencoba membaca hasil hadiah seperti `Rp 5.000`, `Rp 10.000`, `Free Spin`, atau `Zonk`
4. jika hasilnya `5.000` atau `10.000`, bot langsung meneruskan klaim ke admin
5. membalas sesuai hasil yang terbaca

Jika screenshot buram, terpotong, atau OCR belum siap di server, bot akan meminta user kirim ulang atau memberi tahu bahwa OCR belum siap.

#### B. Klaim lewat teks

Bot juga bisa merespons pesan teks user di private chat setelah proses validasi selesai.

Contoh:

- Jika user mengirim teks seperti `lupa screenshot`, `lupa screenshoot`, atau `lupa ss`, bot membalas:

```text
Jika kamu lupa screenshot, maka bonus lucky spin hangus ya!!

Kamu mendapatkan hadiah berapa ya ?
```

- Jika user lalu mengirim nominal hadiah seperti `5000`, `5.000`, `5,000`, `10000`, `10.000`, `10,000`, atau nominal angka lain yang terbaca jelas, bot membalas:

```text
Untuk Selanjutnya nanti kamu jangan lupa Screenshot hasil lucky spin nya ya !
Hadiah kamu saya bantu proseskan, mohon di tunggu !!
```

Lalu bot langsung meneruskan klaim ke admin dengan format yang sama seperti flow screenshot.

- Jika user mengirim teks umum yang masih berkaitan dengan `hadiah`, `bonus`, `spin`, `ss`, `screenshot`, atau `screenshoot`, bot akan mengarahkan user untuk kirim screenshot atau menyebut nominal hadiah.

- Jika user menanyakan `status klaim`, `sudah belum`, `diproses`, atau mengeluh menunggu lama, bot akan membaca status session private chat dan memberi balasan sesuai kondisi:
  - belum ada klaim aktif
  - klaim sudah diteruskan ke admin
  - klaim sudah selesai diproses admin

- Jika user langsung mengirim nominal hadiah tetapi bot belum punya `User ID` tervalidasi pada session itu, bot akan mengarahkan user untuk ambil kode atau kirim `User ID` dulu.

- Jika user menanyakan admin atau bantuan lanjutan, bot akan memberi arahan ke `@horeg222` sambil tetap mencoba mengarahkan flow yang masih bisa ditangani bot.

Teks panduan yang dipakai:

```text
Panduan klaim Lucky Spin:
1. Salin Kode akses yang telah di berikan.
2. Buka halaman Lcuky Spin.
3. Pada Kolom input USER ID kamu masukan user id atau username.
4. Pada kolom input Kode Akses kamu masukan Kode Akses tadi yang telah kamu salin.
5. Setleh semua sudah cocok, klik Tombol Lanjutkan.
6. Setelah nya Kamu sudah bisa melakukan SPIN, Dan Screenshot hasil yang di dapat.
7. Selamat mencoba semoga beruntung ya!! .
```

### 7. Jika User Sudah Pernah Klaim

Jika `User ID` sudah ada di Google Sheet kolom klaim, atau `TELE ID` yang dipakai sudah pernah tercatat klaim, maka Apps Script akan menolak request dan bot membalas pesan penolakan yang sama, misalnya:

```text
Lucky spin dapat di klaim 1 kali dalam 1 hari , info selanjutnya bisa Hub admin @horeg222
```

### 8. Jika Apps Script Bermasalah

Jika request ke Apps Script gagal atau response tidak valid, bot membalas:

```text
Sistem kode akses sedang bermasalah. Coba lagi beberapa saat.
```

## Integrasi Google Apps Script dan Google Sheets

Bot tidak mengambil kode dari file lokal untuk flow private chat. Pengambilan kode sepenuhnya bergantung pada Apps Script.

Alur integrasi:

1. user kirim `User ID` di private chat
2. `bot.py` mengirim request ke `GOOGLE_SCRIPT_URL`
3. Apps Script memeriksa Google Sheet
4. jika `User ID` dan `TELE ID` belum ada, Apps Script mengambil kode kosong dari sheet
5. Apps Script mengisi kolom klaim di sheet
6. Apps Script mengembalikan kode ke bot
7. bot mengirim kode ke user

Kolom sheet yang dipakai:

- Kolom `B`: `KODE`
- Kolom `C`: `NOMINAL`
- Kolom `D`: `USER ID`
- Kolom `E`: `TELE ID`
- Kolom `F`: `WAKTU KLAIM`

Data kode dimulai dari baris `6`.

## State yang Dipakai Bot

Bot memakai `context.user_data` untuk menyimpan langkah percakapan sementara.

State yang dipakai:

- `STEP_PRIVATE_GET_CODE_USER_ID`
  Menandakan bot sedang menunggu `User ID` di private chat.
- `STEP_USER_ID`
  State lama untuk flow klaim di grup.
- `STEP_ACCESS_CODE`
  State lama untuk input kode akses di grup.

Selain state di atas, bot juga menyimpan data session private chat berikut:

- `validated_user_id`
  User ID yang sudah lolos validasi dan dipakai saat meneruskan klaim hadiah ke admin.
- `private_message_history`
  Riwayat singkat pesan private untuk anti-spam pesan berulang.
- `validated_code`
  Kode akses yang sudah lolos validasi lokal.
- `validated_tier`
  Tier kode hasil validasi lokal.

Selain `context.user_data`, bot juga memakai `context.bot_data` untuk menyimpan status klaim private per chat pada key `private_claim_statuses`.
Data ini di-load dari file `private_claim_statuses.json` saat store pertama kali dipakai, lalu disimpan ulang setiap ada perubahan status.
Bot juga membersihkan otomatis status yang tidak diperbarui lebih dari 7 hari agar file penyimpanan tetap kecil.

Status yang dipakai:

- `validated`
  Member sudah lolos validasi `User ID` dan siap spin.
- `awaiting_admin`
  Klaim hadiah sudah dikirim ke admin dan sedang menunggu proses.
- `completed`
  Admin sudah membalas `Done` dan member sudah dikonfirmasi.

Catatan:

- Flow klaim aktif sekarang lebih fokus ke private chat untuk ambil kode.
- State lama di grup masih ada di kode sebagai sisa flow validasi lama.

## Penyimpanan Lokal

### `lucky_spin_usage.json`

Masih dipakai untuk menyimpan timestamp penggunaan kode pada flow validasi lokal yang masih tersisa di `bot.py`.

### `lucky_spin_assignments.json`

Ini adalah file dari sistem assignment lokal lama. Saat ini flow ambil kode via Google Sheets tidak lagi bergantung pada file ini.

### `private_claim_statuses.json`

Dipakai untuk menyimpan status klaim private yang aktif maupun yang sudah selesai, sehingga member masih bisa cek `status klaim` meskipun bot baru saja restart.
Status yang `updated_at`-nya lebih lama dari 7 hari akan dibersihkan otomatis saat data di-load atau saat ada update status baru.

### `private_chat_logs.json`

Dipakai untuk menyimpan histori percakapan private antara member dan bot.
Log ini dipakai oleh dashboard admin dan dibersihkan otomatis jika tidak diperbarui lebih dari 14 hari.
Setiap chat disimpan dengan batas entry terbaru agar ukuran file tetap terkendali.

## Handler Utama di bot.py

Beberapa handler utama:

- `welcome`
  Menyambut member baru di grup.
- `start`
  Menangani `/start` di grup dan private chat.
- `spin`
  Menampilkan menu utama di grup.
- `button_handler`
  Menangani klik tombol inline.
- `handle_claim_input`
  Menangani input percakapan berbasis state.
- `handle_private_spin_screenshot`
  Membaca screenshot hasil Lucky Spin di private chat dan menjalankan OCR.
- `handle_private_general_text`
  Menangani intent chat bebas di private chat seperti panduan, login, status klaim, bantuan, dan follow-up member.
- `admin_dashboard`
  Menampilkan dashboard admin untuk melihat daftar chat member dan isi percakapan private.
- `notify_admin_claim`
  Meneruskan klaim hadiah hasil OCR ke admin.
- `auto_reply`
  Menangani auto reply di grup dan private chat, termasuk trigger `kode akses` dan percakapan teks hadiah.
- `anti_spam`
  Menghapus link yang tidak diizinkan.

## Ringkasan Alur User

### Alur dari Grup ke Private Chat

1. user melihat menu grup
2. user klik `Ambil Kode Akses`
3. user diarahkan ke chat pribadi bot
4. bot meminta `User ID`
5. user mengirim `User ID`
6. bot cek ke Apps Script
7. jika lolos, bot mengirim kode akses
8. user klik `Buka Halaman Lucky Spin`
9. setelah spin, user bisa kirim screenshot hasil atau teks hadiah di private chat
10. jika hadiah valid, bot meneruskan klaim ke admin

### Alur Tombol Klaim di Grup

1. user klik `Klaim Lucky Spin`
2. bot memberi pesan arahan bahwa klaim hanya 1 kali sehari
3. bot meminta user untuk klik `Ambil Kode Akses`

### Alur Klaim Hadiah ke Admin

1. user sudah validasi `User ID` dan menerima kode akses
2. user menyelesaikan spin
3. user kirim screenshot hasil spin atau menyebut nominal hadiah di private chat
4. bot membaca hasil hadiah
5. jika hadiah bernilai klaim, bot mengirim pesan ke admin `@horeg222`
6. admin membalas pesan klaim dengan teks `Done`
7. bot mengirim konfirmasi ke member bahwa hadiah sudah diproses

## Catatan Teknis

- Jika `GOOGLE_SCRIPT_URL` salah atau Apps Script belum di-deploy sebagai Web App, flow private chat tidak akan berhasil.
- Jika file `images/panduan.jpg` tidak ada, panduan private chat tidak akan mengirim gambar.
- Jika OCR lokal belum siap, klaim via screenshot tidak akan terbaca, tetapi user masih bisa menyebut nominal hadiah lewat teks di private chat.
- Token bot Telegram di `.env` harus dijaga. Jika pernah terekspos, segera regenerate lewat BotFather.

## Deploy 24 Jam di Railway

Project ini sudah disiapkan untuk deploy ke Railway dengan file berikut:

- [requirements.txt](c:/Users/Bot-telegram/requirements.txt)
- [railway.json](c:/Users/Bot-telegram/railway.json)
- [.python-version](c:/Users/Bot-telegram/.python-version)

Konfigurasi deploy yang dipakai:

- Railway akan install dependency dari `requirements.txt`
- Railway akan membaca [nixpacks.toml](c:/Users/Bot-telegram/nixpacks.toml) untuk menambahkan package sistem `tesseract`
- Railway akan menjalankan bot dengan command:

```text
python bot.py
```

### Langkah Deploy ke Railway

1. Buat akun di Railway.
2. Push project ini ke GitHub.
3. Di Railway pilih `New Project`.
4. Pilih `Deploy from GitHub repo`.
5. Pilih repository bot ini.
6. Setelah project terbentuk, buka tab `Variables`.
7. Tambahkan environment variables:

```env
BOT_TOKEN=token_bot_kamu
GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/.../exec
```

8. Deploy project.
9. Setelah selesai, buka tab `Deployments` atau `Logs` untuk memastikan bot sudah running.

### Catatan Penting Railway

- Railway Free memberi credit terbatas, jadi cocok untuk mulai dan testing.
- Bot ini memakai `run_polling()`, jadi Railway harus menjalankan proses terus menerus.

## Setup OCR Lokal

Supaya fitur screenshot Lucky Spin bisa bekerja baik di private chat, environment perlu 2 lapis dependency:

1. Python package:
   - `pillow`
   - `pytesseract`
2. System package:
   - `Tesseract OCR`

### Windows Lokal

1. Install package Python:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Install Tesseract OCR:

```powershell
winget install --id=tesseract-ocr.tesseract -e
```

3. Jika perlu, isi `.env`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

4. Jalankan bot:

```powershell
venv\Scripts\python.exe bot.py
```

### Railway

Untuk Railway, package Python akan diambil dari `requirements.txt`, dan engine OCR akan dipasang lewat [nixpacks.toml](c:/Users/Bot-telegram/nixpacks.toml). Setelah file berubah:

1. push perubahan repo
2. lakukan redeploy service di Railway
3. cek log startup bot

Jika deploy berhasil, bot akan bisa membaca screenshot hasil Lucky Spin di private chat tanpa perlu `OPENAI_API_KEY`.
- File lokal seperti `lucky_spin_usage.json` di Railway tidak cocok dijadikan penyimpanan permanen, karena filesystem deploy bisa berubah saat restart atau redeploy.
- Flow utama bot kamu sekarang aman karena pembagian kode akses memakai Google Apps Script dan Google Sheets, bukan file lokal.

### Rekomendasi Sebelum Push ke GitHub

- Pastikan `.env` tidak ikut ter-push.
- Pastikan token bot sudah aman dan tidak pernah dibagikan lagi.
- Pastikan gambar panduan tersedia di:

```text
images/panduan.jpg
```
