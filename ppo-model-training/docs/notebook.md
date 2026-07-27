# 📖 Dokumentasi Teknis Notebook: Optimasi Aeroponik dengan Algoritma PPO

Dokumen ini berisi dokumentasi teknis menyeluruh mengenai program Python/Jupyter Notebook [`Optimasi_Efisiensi_Nutrisi_pada_Sistem_Aeroponik_Melalui_Pengontrolan_Kontinu_Pengkabutan_dengan_Algoritma_PPO.ipynb`](file:///home/almuzky/TA/Microservices/services/ml-control/Optimasi_Efisiensi_Nutrisi_pada_Sistem_Aeroponik_Melalui_Pengontrolan_Kontinu_Pengkabutan_dengan_Algoritma_PPO.ipynb).

---

## 🎯 1. Perumusan Masalah

Budidaya tanaman kentang (*Solanum tuberosum L.*) menggunakan sistem aeroponik membutuhkan pengontrolan mikro-lingkungan yang sangat presisi pada zona perakaran (*root chamber*). Tidak seperti metode hidroponik konvensional yang merendam akar dalam larutan, aeroponik menggantungkan akar di udara dan menghembuskan nutrisi dalam bentuk kabut aerosol (*misting*).

### Tantangan Utama Kontrol Aeroponik:
1. **Dilema Oksigenasi vs. Hidrasi (Hypoxia Trade-Off)**:
   - Jika *misting* dinyalakan terlalu jarang, kelembapan merosot $<85\%$, menyebabkan desikasi (kekeringan) pada bulu-bulu akar mikro ($5-50\ \mu\text{m}$).
   - Jika *misting* dinyalakan terus-menerus tanpa jeda, terbentuk lapisan air (*water film*) tebal pada permukaan akar yang menghambat difusi Oksigen ($\text{O}_2$), memicu **hipoksia/anoksia akar** dan penyakit busuk akar (*Pythium sp.*).
2. **Efisiensi Energi & Larutan Nutrisi**:
   - Pengoperasian pompa tekanan tinggi secara kontinu memboroskan daya listrik dan mempercepat keausan aktuator/nozzle.
3. **Fluktuasi $EC$ dan $pH$**:
   - Penguapan dan penyerapan hara oleh akar menyebabkan pergeseran $pH$ dan konduktivitas listrik ($EC$).

**Solusi Algoritma**: Menggunakan Pembelajaran Penguatan berbasis **Proximal Policy Optimization (PPO)** untuk mempelajari kebijakan kontrol kontinu *intermittent misting* yang optimal secara otomatis. PPO dipilih setelah evaluasi komparatif terhadap A2C dan SAC berdasarkan karakteristik spesifik sistem aeroponik.

---

## 📐 2. Formulasi Ruang Status, Ruang Aksi, dan Fungsi Imbalan

### 2.1 Ruang Status $S(t) \in \mathbb{R}^{10}$

Vektor observasi agent merupakan **gabungan dua modalitas dengan peran berbeda**:

- **Telemetri lingkungan** (setiap 5 detik): `T_in`, `H_in`, `T_out`, `H_out`, `EC`, `pH`, `T_nut`, `I_day` — digunakan agen untuk kontrol mikro-iklim secara *waktu nyata*.
- **Vision** (3–5 capture per hari): `L_root` dan `U_status` — diperbarui sesuai **jadwal timer tetap** (setiap 4 jam sejak mulai episode), bukan bergantung pada kondisi sensor; berfungsi sebagai sinyal evaluasi hasil dari kebijakan kontrol yang telah dilakukan.

$$
S(t) = \begin{bmatrix}
L_{\text{root}}(t) & U_{\text{status}}(t) & T_{\text{in}}(t) & H_{\text{in}}(t) & T_{\text{out}}(t) & H_{\text{out}}(t) & EC(t) & pH(t) & T_{\text{nut}}(t) & I_{\text{day}}(t)
\end{bmatrix}^T
$$

| Variabel | Simbol | Rentang Realistis | Satuan | Deskripsi |
| :--- | :--- | :--- | :--- | :--- |
| Panjang Akar | $L_{\text{root}}$ | $[0.0, 300.0]$ | cm | Panjang akar terukur dari vision (bounding box/segmentasi) |
| Kesehatan Umbi | $U_{\text{status}}$ | $[0.0, 1.0]$ | Ratio | Skor kesehatan umbi dari klasifikasi vision ($1.0 = \text{optimal}$); diestimasi dari frame diambil saat **misting OFF** pada sampel umbi yang tidak tertutup. **Catatan**: $U_{\text{status}}$ merupakan indikasi kondisi fisik umbi, bukan status oksigenasi akar. Oksigenasi zona akar ($O2_{\text{status}}$) adalah *hidden state* yang tidak diakses agen secara langsung |
| Suhu Internal | $T_{\text{in}}$ | $[25.0, 32.0]$ | °C | Suhu udara di dalam *root chamber* (domain-randomized untuk kondisi tropis) |
| :--- | :--- | :--- | :--- | :--- |
| Kelembapan Internal | $H_{\text{in}}$ | $[20.0, 100.0]$ | % RH | Kelembapan relatif ruang akar |
| Suhu Eksternal | $T_{\text{out}}$ | $[15.0, 30.0]$ | °C | Suhu lingkungan luar/rumah kaca |
| Kelembapan Eksternal | $H_{\text{out}}$ | $[20.0, 100.0]$ | % RH | Kelembaban lingkungan luar |
| Konduktivitas Listrik | $EC$ | $[0.5, 3.5]$ | mS/cm | Konsentrasi kation/anion nutrisi |
| Derajat Keasaman | $pH$ | $[4.0, 9.0]$ | - | Keasaman larutan hara |
| Suhu Nutrisi | $T_{\text{nut}}$ | $[18.0, 30.0]$ | °C | Suhu reservoir cairan nutrisi;berlaku dinamika pasif mengikuti $T_{\text{in}}$ dengan time constant ~2 jam |
| Status Pencahayaan | $I_{\text{day}}$ | $\{0, 1\}$ | Binary | $1 = \text{Siang}$, $0 = \text{Malam}$ |

> **Catatan POMDP**: Karena $O2_{\text{status}}$ tersembunyi dari agen dan vision memiliki frekuensi capture yang rendah, sistem ini diformulasikan sebagai **Partially Observable Markov Decision Process (POMDP)**. Agen harus menaksir kondisi oksigenasi, tren pertumbuhan, dan suhu zona akar dari sejarah aksi dan observasi telemetri yang berfrekuensi tinggi. Melalui training, agen diharapkan mempelajari proxy untuk hipoksia dari pola $D_{\text{mist}}$, $interval$, dan $T_{\text{continuous}}$ yang terperangkap dalam network memory.
>
> **Implikasi deploy ke real hardware**: Agent hanya menerima 10 sensor/vision input yang tersedia di hardware nyata. $T_{\text{root}}$ tidak disertakan sebagai observasi; ia tetap berupa estimasi internal simulator untuk memodelkan dinamika pertumbuhan dan penalti lingkungan.

---


### 2.2 Ruang Aksi $A(t) \in \mathbb{R}^3$ & Pemodelan Spray Delay

$$
A(t) = \begin{bmatrix} D_{\text{mist}}(t) & interval_{\text{sec}}(t) & A_{\text{valve}}(t) \end{bmatrix}^T
$$

* $D_{\text{mist}} \in [120.0, 240.0]$ detik: Durasi misting aktif per siklus (2–4 menit), sesuai praktik lapangan kentang aeroponik.
* $interval_{\text{sec}} \in [360.0, 540.0]$ detik: Interval jeda antar siklus semprotan (6–9 menit). Rentang ini dipilih berdasarkan kajian Tunio et al. (2021): interval < 360 detik menyebabkan hipoksia akumulatif, sementara interval > 540 detik menyebabkan desikasi akar mikro (>85% RH threshold).
* $A_{\text{valve}} \in [0.0, 1.0]$: Kontrol katup solenoid untuk **penyemprotan zona bawah akar**. Dipetakan dari ruang aksi ter-normalisasi $[-1, 1]$ dengan threshold **0** (tidak 0.5): jika $a_{\text{valve}} \ge 0$ maka $A_{\text{valve}} = 1.0$, jika $a_{\text{valve}} < 0$ maka $A_{\text{valve}} = 0.0$. Ketika diaktifkan, sistem menyemprot aerosol larutan nutrisi segar di zona bawah akar yang meningkatkan kelembaban lokal, memberikan pendinginan lokal, menjaga oksigenasi, dan secara tidak langsung menyegarkan $EC \to 1.5$ serta $pH \to 6.0$.

#### Pemodelan Spray Delay (*Jeda Pembentukan Tekanan Pompa*)
Pada sistem aeroponik tekanan tinggi ($60–100\text{ PSI}$), terdapat jeda waktu penekanan pipa hidrolik ($t_{\text{delay}} = 1.5\text{ detik}$) dari saat relay pompa menyala hingga katup *anti-tetes* mekar menghembuskan kabut aerosol. Durasi pengkabutan efektif ($D_{\text{effective}}$) yang menyentuh akar dirumuskan sebagai:

$$
D_{\text{effective}} = \max\left(0.0,\; D_{\text{mist}} - 1.5\right)
$$

Jika $D_{\text{mist}} \le 1.5\text{s}$, tidak ada kabut cairan yang keluar ($D_{\text{effective}} = 0$), namun energi listrik pompa tetap terpotong, yang mendidik agen RL untuk memilih pulsa semprotan efektif $> 1.5\text{s}$ agar ada kabut yang benar-benar menyentuh akar.

---

### 2.3 Perumusan Fungsi Imbalan $R(t)$

Fungsi imbalan dirancang untuk menyeimbangkan 6 komponen utama:

$$
R(t) = R_{\text{growth}}(t) + R_{\text{state}}(t) + P_{\text{diversity}}(t) - C_{\text{resource}}(t) - P_{\text{env}}(t) - P_{\text{hypoxia}}(t) - P_{\text{interval}}(t)
$$

> **Catatan temporal**: $R_{\text{growth}}$ hanya tersedia saat capture vision baru (3–5 kali/hari), sedangkan $R_{\text{state}}$, $P_{\text{diversity}}$, $C_{\text{resource}}$, $P_{\text{env}}$, $P_{\text{hypoxia}}$, dan $P_{\text{interval}}$ dihitung setiap langkah. Agar agent tidak hanya mengoptimalkan komponen dense yang lebih sering muncul, `R_growth` diskalakan dengan bobot $w_{\text{growth}} = 25.0$. Antarcapture, reward pertumbuhan di-hold dari nilai terakhir; tidak ada interpolasi. Selain itu, agent mendapatkan **survival bonus** $+0.5$ per langkah untuk mendorong bertahan selama seluruh episode 24 jam.

1. **Imbalan Pertumbuhan Akar ($R_{\text{growth}}$)**:
    $$R_{\text{growth}}(t) = w_{\text{growth}} \cdot \Delta L_{\text{root}}$$
    Di mana $\Delta L_{\text{root}}$ adalah selisih panjang akar antara dua capture vision berturut-turut. Reward ini hanya dihitung saat capture vision baru tersedia.
2. **Biaya Konsumsi Energi ($C_{\text{resource}}$)**:
    $$C_{\text{resource}}(t) = w_{\text{valve\_cost}} \cdot \mathbb{I}(A_{\text{valve}} \ge 0.5)$$
    Biaya hanya dikenakan per aktivasi katup solenoid, bukan per detik misting. Ini mencegah agent meminimalkan $D_{\text{mist}}$ hanya untuk menghemat biaya.
3. **Penalti Lingkungan ($P_{\text{env}}$)**:
    $$P_{\text{env}}(t) = w_{\text{env}} \cdot \left[ \mathbb{I}(pH \notin [5.5, 6.5]) \cdot |pH - 6.0| + \mathbb{I}(EC \notin [1.2, 2.0]) \cdot |EC - 1.6| + \mathbb{I}(H_{\text{in}} < 85\%) \cdot (85 - H_{\text{in}}) \right]$$
    Memberikan penalti linear per satuan deviasi dari setpoint optimal: $pH = 6.0$, $EC = 1.6$, $H_{\text{in}} = 85\%$.
4. **Penalti Hipoksia Akar ($P_{\text{hypoxia}}$)**:
    $$P_{\text{hypoxia}}(t) = w_{\text{hypoxia}} \cdot \max\left(0.0,\; 1.0 - O2_{\text{status}}(t)\right)$$
    - $O2_{\text{status}}(t)$: Indeks oksigenasi internal (variabel tersembunyi simulator), dihitung dari dinamika misting dan **bukan** bagian dari vektor status observasi $U_{\text{status}}$.
5. **Penalti Stres Interval ($P_{\text{interval}}$)**:
    $$P_{\text{interval}}(t) = w_{\text{interval}} \cdot \mathbb{I}(interval_{\text{current}} > 1800)$$
    Menghindari stres osmoregulasi akar akibat jeda pengkabutan yang terlalu panjang (>30 menit) meskipun $H_{\text{in}}$ masih di atas threshold 85%.
6. **State Bonus ($R_{\text{state}}$)**:
    Reward ekstra untuk menjaga parameter lingkungan dalam rentang optimal:
    - $pH \in [5.5, 6.5]$: +0.05
    - $EC \in [1.2, 2.0]$: +0.05
    - $H_{\text{in}} \ge 85\%$: +0.05
    - $T_{\text{root}} \in [10, 20]$: +0.1
    - $O2_{\text{status}} \ge 0.6$: +0.05
    - $D_{\text{mist}} \ge 150.0$: +0.3
    - $390 \le interval_{\text{sec}} \le 480$: +0.2
    - Penalty untuk $D_{\text{mist}} < 130.0$: -1.0
    - Penalty untuk $interval_{\text{sec}} < 360.0$: -0.5
7. **Action Diversity Bonus ($P_{\text{diversity}}$)**:
    Bonus untuk mendorong eksplorasi yang beragam:
    - $\text{std}(D_{\text{mist}}) > 10.0$: +2.0
    - $\text{std}(interval) > 20.0$: +1.0
    - $\ge 2$ kali pergantian $A_{\text{valve}}$: +0.5

---

## 🔬 3. Formulasi Fisika & Fisiologi Lingkungan Simulasi (`AeroponicSimulatorEnv`)

Simulator dibangun menggunakan standar `gymnasium.Env` dengan skala waktu terkalibrasi:
$$\Delta t = 1 \text{ menit per step}, \quad 1 \text{ episode} = 1440 \text{ steps} \approx 24 \text{ jam (1 hari real-time)}$$

`AeroponicSimulatorEnv` menggunakan kelas-kelas pembantu berikut untuk menghindari duplikasi kode:
- `AeroponicStateSpace`: membungkus vektor status menjadi objek bernama.
- `AeroponicActionSpace`: memvalidasi dan menyajikan aksi aktuator.
- `AeroponicRewardFunction`: menghitung total imbalan $R(t)$ secara terpusat, termasuk komponen hipoksia.

### 3.1 Dinamika Pertumbuhan Akar (Terdefinisi dari *Root Elongation Rate*)

Dalam simulator, `L_root` diperlakukan sebagai **observasi visual murni dari kamera**. Untuk menghasilkan nilai `L_root` yang realistis, simulator menggunakan model pertumbuhan logistik termodifikasi berikut:

$$
L_{\text{root}}(t+1) = L_{\text{root}}(t) + r_{\text{step}} \cdot L_{\text{root}}(t) \cdot \left(1 - \frac{L_{\text{root}}(t)}{K}\right) \cdot f(H_{\text{in}}) \cdot f(\text{O}_2) \cdot f(T_{\text{root}}) \cdot \text{Multiplier}_{\text{day/night}}
$$

Konfigurasi parameter:

* $r_{\text{step}} = 0.000833 \text{ cm/min}$: Dikalibrasi dari laju pertumbuhan akar kentang riil $1.2\text{ cm/hari}$ (*Ritter et al., 2001*).
* $K = 300.0\text{ cm}$: Kapasitas maksimum zona perakaran.
* $f(H_{\text{in}}) = \min\left(1.0,\; \frac{H_{\text{in}}(t)}{90.0}\right)$: Faktor kecukupan kelembapan.
* $\text{Multiplier}_{\text{day/night}} = 1.2$ (Siang) / $0.6$ (Malam): Modulasi pertumbuhan berdasarkan fotoperiode.

> **Hubungan Simulator–Kamera**: Hasil dari persamaan ini dianggap sebagai **input dari kamera virtual**. Dalam real hardware, nilai yang sama dihasilkan oleh kamera overhead melalui bounding box/segmentasi akar. Kedua sumber ini harus konsisten: satuan cm, merepresentasikan kedalaman vertikal akar, dan dikalibrasi oleh Ritter et al. (2001).

#### 3.1.1 Pipeline Vision ke Observasi State

`L_root` adalah observasi visual murni dari kamera overhead. Di simulator, nilai ini dihasilkan oleh model pertumbuhan yang dikalibrasi agar sesuai dengan pengukuran dunia nyata.

**Di real hardware:**
1. **Pengambilan gambar**: Frame diambil saat **misting OFF** dengan sampel umbi yang tidak tertutup, 3–5 kali per hari.
2. **Bounding box / segmentasi**: Akar terdeteksi dan diukur untuk menghasilkan *Maximum Vertical Root Depth* — jarak tegak lurus dari pangkal ke ujung akar paling bawah.
3. **Kalibrasi**: Hasil piksel dikonversi ke satuan cm melalui transformasi proyektif kamera.

**Di simulator:**
- Model pertumbuhan logistik menghasilkan nilai `L_root` yang mewakili hasil pengukuran visual tersebut.
- Agresi parameter dirancang agar laju pertumbuhan sekitar **1.2 cm/hari**, sesuai dengan eksperimen Ritter et al. (2001) untuk kentang aeroponik.

> **Penekanan**: `L_root` bukanlah jumlah total biomassa akar, melainkan **kedalaman vertikal akar terukur dari kamera**. Simulator mensimulasikan pertumbuhan akar, dan hasilnya dianggap sebagai pengukuran kamera virtual.

> **Catatan**: `U_status` dan `L_root` sama-sama diperbarui hanya saat capture vision. Di luar waktu capture, kedua variabel ini di-hold dari nilai terakhir. `U_status` merupakan estimasi dari model klasifikasi vision, bukan variabel yang dihitung dari dinamika lingkungan.


### 3.2 Dinamika Suhu Root Zone & Pendinginan ($T_{\text{root}}$ dan $f(T_{\text{root}})$)

$T_{\text{root}}$ merupakan **estimasi internal simulator** untuk suhu zona perakaran, karena sistem sensor nyata hanya menyediakan suhu udara internal $T_{\text{in}}$, bukan suhu permukaan akar secara langsung. Estimasi ini diperbarui berdasarkan dua dinamika:

- **Pendinginan evaporatif** saat misting aktif
- **Pertukaran kalor** dengan udara internal saat misting mati (*Kuncoro et al., 2021*)

$$
T_{\text{root}}(t+1) = \begin{cases}
T_{\text{root}}(t) - 0.3^\circ\text{C}, & \text{jika Misting ON} \\
T_{\text{root}}(t) + \left(T_{\text{in}}(t) - T_{\text{root}}(t)\right) \times 0.05, & \text{jika Misting OFF}
\end{cases}
$$

Faktor pengali suhu pertumbuhan $f(T_{\text{root}})$ kentang (optimal $10-20^\circ\text{C}$ per Kuncoro et al., 2021):

$$
f(T_{\text{root}}) = \begin{cases}
1.0, & 10 \le T_{\text{root}} \le 20 \\
\max\left(0.3, 1.0 - (10 - T_{\text{root}}) \times 0.1\right), & T_{\text{root}} < 10 \\
\max\left(0.3, 1.0 - (T_{\text{root}} - 20) \times 0.15\right), & T_{\text{root}} > 20
\end{cases}
$$

> **Catatan**: $T_{\text{root}}$ bukan variabel observasi dari sensor; ia adalah *estimated state* yang dihitung simulator berdasarkan $T_{\text{in}}$ dan status misting. Agent tidak memiliki pengukuran langsung untuk suhu akar.

### 3.2.1 Dinamika Suhu Nutrisi ($T_{\text{nut}}$)

Suhu reservoir nutrisi $T_{\text{nut}}$ merupakan variabel pasif yang mengadopsi suhu udara dalam $T_{\text{in}}$ secara perlahan karena inersia termal besar reservoir 200L. Dinamika ini dirancahkan berdasarkan literatur pendinginan reservoir hydroponik (Chowdhury et al., 2020):

$$
T_{\text{nut}}(t+1) = T_{\text{nut}}(t) + \alpha \cdot (T_{\text{in}}(t) - T_{\text{nut}}(t)) - \beta \cdot \mathbb{1}_{\text{misting\_on}}
$$

dengan parameter:
- $\alpha = 0.008$ per menit: koefisien drift termal (time constant ≈ 2 jam)
- $\beta = 0.05$ °C/menit: efek pendinginan saat misting aktif
- Batas fisika: $T_{\text{nut}} \in [18, 30]$ °C

Saat misting aktif, Reservoir mendapatkan efek pendinginan evaporatif langsung. Eksternal, $T_{\text{nut}}$ tetap > $T_{\text{root karena kalor spesifik air yang tinggi.

$T_{\text{nut}}$ **bukan variabel kontrol** bagi agen; ia hanya respons pasif terhadap kondisi lingkungan. Namun, agent dapat memanfaatkan sinyal $T_{\text{nut}}$ sebagai **indikator thermal inertia sistem** untuk mengantisipasi kebutuhan pendinginan.

### 3.3 Dinamika Oksigenasi & Hipoksia Akar ($f(\text{O}_2)$)
Mengikuti temuan *Lakhiar et al. (2018)*, pengkabutan berlebihan yang berlangsung terus-menerus tanpa interval kering mengurangi indeks oksigenasi akar:

$$
f(\text{O}_2) = \max\left(0.2,\; 1.0 - 0.08 \times \max(0, T_{\text{continuous}} - 3)\right)
$$

di mana $T_{\text{continuous}}$ adalah hitungan siklus pengkabutan berturut-turut tanpa jeda respirasi. Indeks oksigenasi internal $O2_{\text{status}}$ ini digunakan untuk komponen penalti hipoksia $P_{\text{hypoxia}}$, **bukan** variabel observasi $U_{\text{status}}$ yang kini merepresentasikan kesehatan umbi.

#### 3.3.1 Indeks Oksigenasi Internal (Hidden State)

Indeks oksigenasi internal didefinisikan secara formal sebagai:

$$O2_{\text{status}}(t) = f(\text{O}_2) = \max\left(0.2,\; 1.0 - 0.08 \times \max(0, T_{\text{continuous}}(t) - 3)\right)$$

$O2_{\text{status}}(t)$ adalah variabel tersembunyi (*hidden state*) yang tidak diakses agen. Variabel ini hanya digunakan untuk menghitung komponen penalti hipoksia $P_{\text{hypoxia}}(t)$.

$T_{\text{continuous}}$ adalah counter yang menghitung jumlah siklus pengkabutan berturut-turut tanpa jeda respirasi minimal 60 detik. Counter bertambah 1 setiap kali terjadi misting ON (`D_{\text{effective}} > 0`). Counter ini di-reset ke 0 ketika ada jeda misting $\ge 60$ detik, sesuai waktu respirasi akar minimum sebelum aerasi anaerobik terjadi.

### 3.4 Dinamika Kelembapan Relatif ($H_{\text{in}}$)
Menggunakan respons eksponensial order-pertama:

$$
H_{\text{in}}(t+1) = H_{\text{target}} - \left(H_{\text{target}} - H_{\text{in}}(t)\right) \cdot e^{-\lambda}
$$

* **Saat Misting ON**: $H_{\text{target}} = 98.0\%$, $\lambda = 0.2$ (kelembapan naik cepat).
* **Saat Misting OFF**: $H_{\text{target}} = H_{\text{out}}$, $\lambda = 0.02 + 0.03 \cdot \max(0, \frac{T_{\text{out}} - 20}{15})$ (peluruhan dipercepat oleh suhu tinggi, *Tunio et al., 2021*).

Suhu luar $T_{\text{out}}$ mempengaruhi laju penguapan: saat $T_{\text{out}} > 20$°C, laju penguapan bertambah secara linier hingga maksimum $\lambda = 0.05$ pada $T_{\text{out}} = 35$°C. Ini menangkap fisika bahwa udara panas menyerap kelembaban lebih cepat dari chamber tertutup.

### 3.5 Dinamika Kimia Larutan ($EC$ dan $pH$)
* **Evaporasi EC**: Saat misting OFF dan $H_{\text{in}} < 85\%$, terjadi penguapan air yang menaikkan konsentrasi garam secara linier: $\Delta EC = +0.00033\text{ mS/cm per menit}$ ($\approx 0.02\text{ mS/cm per jam}$, *Tibbitts et al., 2002*).
* **Drift pH**: Penyerapan ion nutrisi oleh akar memicu pergeseran keasaman $\Delta pH = +0.00017\text{ per menit}$ ($\approx 0.01\text{ per jam}$).
* **Penyegaran Nutrisi Bawah**: Pengkabutan utama atau pengkabutan zona bawah via katup solenoid ($A_{\text{valve}} \ge 0.5$) menghembuskan aerosol larutan hara segar yang **mengembalikan** $EC$ ke $1.5$ dan $pH$ ke $6.0$.
* **Efek Pengenceran Saat Misting**: Saat misting aktif, air segar masuk ke chamber dan mengenceran larutan nutrisi secara halus: $\Delta EC = +(1.6 - EC) \times 0.005$ per langkah. Ini menangkap fisika bahwa kabut aeroponik mengandung air murni yang mendilusi konsentrasi nutrisi.

### 3.6 Stokastisitas Lingkungan & Kriteria Terminasi Dini

Simulator menggunakan profil harian deterministik untuk $T_{\text{in}}$, $T_{\text{out}}$, dan $H_{\text{out}}$ yang di-*overlay* dengan fluktuasi stokastik dan event acak:

**Profil Harian Deterministik:**
* **Suhu dalam ($T_{\text{in}}$)**: Siang 26–32°C, malam 22–24°C, dengan domain randomization.
* **Suhu luar ($T_{\text{out}}$)**: Diatur oleh profil harian dan event acak; berkorelasi dengan $T_{\text{in}}$.
* **Kelembaban luar ($H_{\text{out}}$)**: Terkorelasi terbalik dengan suhu: 60–90% tergantung waktu dan kondisi cuaca.

**Fluktuasi Stokastik:**
* **Sensor Noise**: $T_{\text{in}}, T_{\text{out}}$: ±0.3°C; $H_{\text{in}}, H_{\text{out}}$: ±2% RH; $EC$: ±0.1 mS/cm; $pH$: ±0.1 unit; $T_{\text{nut}}$: ±0.15°C.
* **Actuator Noise**: $D_{\text{mist}}$ aktual: ±5%; spray delay: 1.5s ±0.3s; $A_{\text{valve}}$: ±5%.
* **Perturbasi Keasaman**: Drift $pH$ diberi gangguan stokastik $+0.00017 \times \max(1.0, |\mathcal{N}(1.0, 0.3)|)$.

**Event Acak:**
* **Heat Wave (10%)**: $T_{\text{in}} +3–5$°C selama 2–4 jam.
* **Cold Snap (15%)**: $T_{\text{in}} -3–5$°C selama 2–3 jam.
* **Hujan (30%)**: $H_{\text{out}} +10–15$% selama 1–3 jam.

**Kriteria Terminasi Dini (Early Stopping / Failure)**:
Episode dinyatakan *terminated* (gagal) jika parameter kimia keluar dari ambang batas aman fisiologis tanaman kentang:
$$pH < 4.2 \text{ atau } pH > 8.5 \quad \text{atau} \quad EC < 0.6 \text{ atau } EC > 3.2$$

> **Catatan**: Ambang batas ini bertujuan sebagai *safety net*. Dari drift normal, early stopping tidak akan tertrigger oleh drift deterministik dalam episode 24 jam, tetapi bisa terjadi akibat kombinasi drift stokastik + heat wave + error kontrol.

### 3.7 Vision Sampling Schedule

Capture vision untuk `L_root` dan `U_status` dilakukan pada **interval tetap** setiap hari:
- **Waktu capture**: jam ke-4, 8, 12, 16, dan 20 (WIB)
- **Durasi capture**: 10 detik per tank
- **Kondisi**: hanya saat **misting OFF** dengan sampel umbi yang tidak tertutup
- **Fallback**: jika $H_{\text{in}} > 90\%$ (kabut teks), capture ditunda 30 menit. Jika gagal berturut-turut > 2 capture, kontrol dialihkan ke mode fallback berbasis aturan.

### 3.8 Episode Initialization & Reset

Setiap episode dimulai dengan kondisi awal yang konsisten untuk memastikan reproduktibilitas:

| Parameter | Nilai Awal | Justifikasi |
| :--- | :--- | :--- |
| $L_{\text{root}}$ | $8.0\text{ cm}$ | Asumsi awal berdasarkan ukuran mini-tuber kentang muda; dapat disesuaikan sesuai varietas |
| $U_{\text{status}}$ | $0.95$ | Status kesehatan umbi awal dalam kondisi baik |
| $T_{\text{in}}$ | $27.0 \pm 2.0\text{ °C}$ | Suhu awal greenhouse: baseline 27°C (rata-rata tropis) ±2°C; domain randomization untuk menangani variasi musim kemarau/dingin |
| $H_{\text{in}}$ | $82.0 \pm 10.0\text{% RH}$ | Kelembaban awal: baseline 82% ±10% untuk menghadapi variasi kelembaban tropis |
| $T_{\text{out}}$ | $28.0\text{ °C}$ | Suhu lingkungan luar awal diikuti profil harian realistis (tropis) |
| $H_{\text{out}}$ | $70.0\text{% RH}$ | Kelembaban lingkungan luar awal diikuti profil harian realistis |
| $EC$ | $1.7 \pm 0.3\text{ mS/cm}$ | Konsentrasi nutrisi awal: baseline 1.7 ±0.3 untuk variasi lapangan |
| $pH$ | $5.9 \pm 0.3$ | Keasaman larutan awal: baseline 5.9 ±0.3 untuk variasi lapangan |
| $T_{\text{nut}}$ | $T_{\text{in}} \pm 1.0\text{ °C}$ | Suhu reservoir nutrisi awal mengikuti $T_{\text{in}}$ dengan drift pasif (time constant ~2 jam); di-randomize sekitar nilai awal $T_{\text{in}}$ |
| $I_{\text{day}}$ | $1$ | Episode dimulai pada siang hari |

Episode berakhir ketika:
1. **Waktu mencapai 24 jam** (86400 detik), atau
2. **Early stopping**: $pH < 4.2$ atau $pH > 8.5$ atau $EC < 0.6$ atau $EC > 3.2$

#### 3.8.1 Domain Randomization untuk Kondisi Lingkungan Tropis

Setiap episode menerapkan domain randomization untuk mensimulasikan variabilitas kondisi greenhouse di Indonesia:

- **$T_{\text{in}}$**: $27.0 \pm 2.0\text{ °C}$ (baseline musim kemarau)
- **$H_{\text{in}}$**: $82.0 \pm 10.0\text{% RH}$
- **$EC$**: $1.7 \pm 0.3\text{ mS/cm}$
- **$pH$**: $5.9 \pm 0.3$

Agen dilatih robust terhadap fluktuasi ini, bukan hanya satu kondisi spesifik.

#### 3.8.2 Profil Harian Realistis (Musim Kemarau, Juli)

Simulator menggunakan profil suhu dan kelembaban yang di-modelkan berdasarkan kondisi greenhouse tropis di Indonesia:

**Suhu udara dalam ($T_{\text{in}}$):**
- Pagi (06:00–09:00): 26–28°C
- Siang (09:00–15:00): 28–32°C (puncak 12:00)
- Sore (15:00–18:00): 26–28°C
- Malam (18:00–06:00): 22–24°C

**Kelembaban dalam ($H_{\text{in}}$):**
- Pagi: 80–85%
- Siang: 70–80%
- Sore: 75–85%
- Malam: 85–95%

**Suhu luar ($T_{\text{out}}$):**
- Sedikit lebih panas dari $T_{\text{in}}$ saat siang (+2°C)
- Hampir sama dengan $T_{\text{in}}$ saat malam (+1°C)
- Rentang: 23–33°C

**Kelembaban luar ($H_{\text{out}}$):**
- Terkorelasi terbalik dengan suhu: lebih rendah saat hari (60–75%), lebih tinggi saat malam (75–90%)
- Musim kemarau: bisa turun ke 50–60% saat siang

#### 3.8.3 Event Random Acak

Setiap episode memiliki probabilitas mengalami event lingkungan acak:

1. **Heat Wave (10% kemungkinan):**
   - $T_{\text{in}}$ naik +3–5°C selama 2–4 jam
   - Biasanya terjadi 10:00–14:00
   - Meningkatkan tekanan pendinginan pada akar

2. **Cold Snap (15% kemungkinan):**
   - $T_{\text{in}}$ turun -3–5°C selama 2–3 jam
   - Biasanya terjadi 02:00–05:00
   - Menurunkan laju evapotranspirasi

3. **Hujan/Rain (30% kemungkinan):**
   - $H_{\text{out}}$ naik +10–15% selama 1–3 jam
   - Meningkatkan kelembaban luar, mengurangi tekanan evaporasi
   - Biasanya terjadi 08:00–16:00

Event ini memaksa agent beradaptasi dengan kondisi non-stasioner, meningkatkan ketahanan policy untuk deploy ke hardware nyata.

#### 3.8.4 Sensor dan Actuator Noise

Untuk simulasi yang lebih realistis, simulator menambahkan:

**Sensor Noise (diobservasi agent):**
- $T_{\text{in}}$, $T_{\text{out}}$: ±0.3°C
- $H_{\text{in}}$, $H_{\text{out}}$: ±2% RH
- $EC$: ±0.1 mS/cm
- $pH$: ±0.1 unit
- $T_{\text{nut}}$: ±0.15°C

**Actuator Noise (diperankan agent):**
- $D_{\text{mist}}$ aktual: ±5% dari nilai yang diperintahkan
- Spray delay: 1.5s ±0.3s variansi
- $A_{\text{valve}}$: ±5% dari nilai yang diperintahkan

Noise ini mendorong agent belajar policy yang lebih robust terhadap ketidakpastian sensor dan aktuator di lapangan.

### 3.9 Reward Weights & Scaling

Bobot komponen reward ditetapkan melalui manual tuning untuk menjaga keseimbangan antara pertumbuhan, efisiensi, dan keselamatan tanaman:

| Bobot | Nilai | Komponen | Justifikasi |
| :--- | :--- | :--- | :--- |
| $w_{\text{growth}}$ | $25.0$ | $R_{\text{growth}}$ | Skala reward pertumbuhan absolut ($\Delta L_{\text{root}}$ per capture vision) |
| $w_{\text{mist\_cost}}$ | $0.002$ | $C_{\text{resource}}$ | Tidak digunakan lagi; biaya per detik misting dihapus untuk mencegah agent meminimalkan $D_{\text{mist}}$ |
| $w_{\text{valve\_cost}}$ | $0.15$ | $C_{\text{resource}}$ | Biaya per aktivasi katup bawah, moderate untuk mengontrol frekuensi |
| $w_{\text{env}}$ | $0.05$ | $P_{\text{env}}$ | Penalti per satuan deviasi dari rentang optimal pH/EC/H_in |
| $w_{\text{hypoxia}}$ | $0.02$ | $P_{\text{hypoxia}}$ | Penalti untuk kondisi hipoksia, karena keselamatan akar adalah prioritas tinggi |
| $w_{\text{interval}}$ | $0.01$ | $P_{\text{interval}}$ | Penalti binary saat interval > 1800 detik, mencegah stres osmoregulasi |

#### 3.9.1 Reward Komponen Pertumbuhan untuk Capture Pertama

Untuk capture vision pertama dalam episode, reward pertumbuhan dihitung relatif terhadap kondisi awal:

$$R_{\text{growth}}(t_{\text{first capture}}) = w_{\text{growth}} \cdot \frac{L_{\text{root}}(t_{\text{capture}}) - L_{\text{root}}(0)}{\Delta t_{\text{capture}}}$$

Untuk capture berikutnya, digunakan selisih terhadap nilai $L_{\text{root}}$ pada capture sebelumnya.

### 3.10 Penanganan Aksi & Pembatasan

Karena PPO menghasilkan aksi kontinu dari distribusi Gaussian, wrapper Gymnasium menerima aksi dalam rentang ter-normalisasi $[-1, 1]$ untuk semua 3 dimensi, lalu memetakannya ke rentang fisik aktuator sebelum diproses simulator. Simulator menggunakan model **timer-based misting cycle**, dimana setiap aksi menentukan satu siklus lengkap:

- $a_{\text{mist}} \in [-1, 1] \mapsto D_{\text{mist}} \in [120.0, 240.0]$ — durasi fase ON dalam detik (2–4 menit)
- $a_{\text{interval}} \in [-1, 1] \mapsto interval_{\text{sec}} \in [360.0, 540.0]$ — durasi fase OFF dalam detik (6–9 menit)
- $a_{\text{valve}} \in [-1, 1] \mapsto A_{\text{valve}} \in \{0.0, 1.0\}$ — threshold **0** (tidak 0.5): jika $a_{\text{valve}} \ge 0$ maka $A_{\text{valve}} = 1.0$, jika $a_{\text{valve}} < 0$ maka $A_{\text{valve}} = 0.0$

$A_{\text{valve}}$ diperlakukan sebagai nilai biner. Threshold $\ge 0.5$ digunakan hanya untuk menentukan apakah katup aktif (ON) atau tidak (OFF) saat menghitung biaya $C_{\text{resource}}$.

### 3.11 Step Transition Order (Timer-Based Cycle)

Setiap langkah simulator sekarang merupakan **satu siklus misting lengkap**:

1. **Masukan aksi** dari agen: $[D_{\text{mist}}, interval_{\text{sec}}, A_{\text{valve}}]$
2. **Fase ON**: Jalankan misting selama $D_{\text{mist}}$ detik dengan update state setiap 1 menit
3. **Hitung $D_{\text{effective}}$** dengan spray delay $1.5\text{ detik}$
4. **Fase OFF**: Matikan misting selama $interval_{\text{sec}}$ detik dengan update state setiap 1 menit
5. **Update $I_{\text{day}}$** berdasarkan waktu simulasi
6. **Update capture vision** setiap 4 jam sejak mulai episode (timer-based, bukan sensor-based)
7. **Update $L_{\text{root}}$ dan $U_{\text{status}}$** hanya saat capture vision terjadi
8. **Hitung imbalan** $R(t)$ untuk siklus tersebut
9. **Cek terminasi dini** jika $pH$ atau $EC$ keluar dari rentang aman
10. **Kembalikan** $(S(t+1), R(t), terminated, truncated, info)$

> **Catatan**: Episode terdiri dari banyak siklus misting hingga total waktu mencapai 24 jam. Setiap siklus menghasilkan satu reward yang dihitung dari rata-rata state selama siklus tersebut.

---


## 💻 4. Integrasi & Pelatihan Algoritma PPO

Program menggunakan library `stable-baselines3` dengan arsitektur **Actor-Critic (MlpPolicy)**. wrapper Gymnasium menerima aksi ter-normalisasi $[-1, 1]$ dan memetakannya ke rentang fisik sebelum dikirim ke simulator:

```python
from aeroponic_simulator import AeroponicSimulatorEnv
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3.common.callbacks import BaseCallback

class AeroponicGymnasiumEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.sim = AeroponicSimulatorEnv()
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 15.0, 20.0, 15.0, 20.0, 0.5, 4.0, 18.0, 0.0], dtype=np.float32),
            high=np.array([300.0, 1.0, 30.0, 100.0, 30.0, 100.0, 3.5, 9.0, 25.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.D_mist_min = 120.0
        self.D_mist_max = 240.0
        self.interval_min = 360.0
        self.interval_max = 540.0

    def _map_action(self, action):
        a_01 = (action + 1.0) / 2.0
        D_mist = self.D_mist_min + a_01[0] * (self.D_mist_max - self.D_mist_min)
        interval = self.interval_min + a_01[1] * (self.interval_max - self.interval_min)
        A_valve = 1.0 if action[2] >= 0.0 else 0.0
        return [D_mist, interval, A_valve]

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)
        physical_action = self._map_action(action)
        state, reward, terminated, truncated, info = self.sim.step(physical_action)
        return np.array(state, dtype=np.float32), float(reward), terminated, truncated, info

# Vektor lingkungan dengan normalisasi observasi dan reward
vec_env = make_vec_env(AeroponicGymnasiumEnv, n_envs=1)
vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

# Callback: adaptive entropy coefficient
class AdaptiveEntropyCallback(BaseCallback):
    def __init__(self, ent_start=0.2, ent_end=0.03, boost_factor=1.5, window_size=10):
        super().__init__()
        self.ent_start = ent_start
        self.ent_end = ent_end
        self.boost_factor = boost_factor
        self.window_size = window_size
        self.entropy_window = []
        self.entropy_min = 0.3
        self.entropy_max = 2.5

    def _on_rollout_end(self):
        if hasattr(self.model, 'rollout_buffer') and self.model.rollout_buffer is not None:
            buf = self.model.rollout_buffer
            if hasattr(buf, 'old_log_prob') and buf.old_log_prob is not None:
                log_probs = buf.old_log_prob
                ent_val = float(-log_probs.mean()) if hasattr(log_probs, 'mean') else float(-np.mean(log_probs))
                self.entropy_window.append(ent_val)
                if len(self.entropy_window) > self.window_size:
                    self.entropy_window.pop(0)
                avg_ent = sum(self.entropy_window) / len(self.entropy_window)
                progress = min(1.0, self.num_timesteps / 500000)
                base_ent = self.ent_start + (self.ent_end - self.ent_start) * progress
                if avg_ent < self.entropy_min:
                    new_ent = min(base_ent * self.boost_factor, self.entropy_max)
                elif avg_ent > self.entropy_max:
                    new_ent = max(base_ent * 0.7, self.entropy_min)
                else:
                    new_ent = base_ent
                self.model.ent_coef = new_ent
        return True

# Callback: value normalization tracking
class ValueNormalizationCallback(BaseCallback):
    def __init__(self, alpha=0.99):
        super().__init__()
        self.alpha = alpha
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.count = 0

    def _on_step(self):
        if hasattr(self.model, 'rollout_buffer'):
            buf = self.model.rollout_buffer
            if buf is not None and hasattr(buf, 'rewards'):
                rewards = buf.rewards
                if len(rewards) > 0:
                    batch_mean = np.mean(rewards)
                    batch_std = np.std(rewards) + 1e-8
                    self.count += len(rewards)
                    self.reward_mean = self.alpha * self.reward_mean + (1 - self.alpha) * batch_mean
                    self.reward_std = self.alpha * self.reward_std + (1 - self.alpha) * batch_std
        return True

# Linear learning rate schedule
def linear_schedule(initial_value, final_value=1e-5):
    def func(progress_remaining):
        return final_value + (initial_value - final_value) * progress_remaining
    return func

# Inisialisasi Model PPO
model = PPO(
    policy="MlpPolicy",
    env=vec_norm,
    learning_rate=linear_schedule(3e-4, 1e-5),
    n_steps=4096,
    batch_size=128,
    n_epochs=10,
    gamma=0.995,
    ent_coef=0.05,
    vf_coef=0.5,
    max_grad_norm=1.0,
    clip_range=0.1,
    gae_lambda=0.95,
    verbose=1,
    tensorboard_log="./aeroponic_ppo_tensorboard/",
    device="cpu",
)

# Pelatihan Agen dengan callback
callbacks = [AdaptiveEntropyCallback(ent_start=0.2, ent_end=0.03), ValueNormalizationCallback()]
model.learn(total_timesteps=500000, callback=callbacks)
model.save("models/aeroponic_ppo.zip")
vec_norm.save("models/vec_normalize.pkl")
```

> **Catatan**: `make_vec_env` dan `VecNormalize` digunakan untuk stabilisasi training. Pastikan statistik `VecNormalize` disimpan dan dimuat kembali saat evaluasi untuk mencegah *distribution shift*.

### 4.1 Arsitektur Jaringan Syaraf & Normalisasi `VecNormalize`
1. **Arsitektur Actor-Critic MLP**: Policy network ($\pi_\theta$) dan Value network ($V_\phi$) menggunakan arsitektur Multi-Layer Perceptron dengan 2 *hidden layers* (masing-masing 64 neuron) dan fungsi aktivasi `Tanh`.
   - **Actor Head**: Mengeluarkan rata-rata $\mu(s)$ dan deviasi standar $\sigma$ untuk distribusi Gaussian aksi 3D ($D_{\text{mist}}, interval_{\text{sec}}, A_{\text{valve}}$).
   - **Critic Head**: Memprediksi estimasi nilai *State-Value* $V(s)$ untuk menghitung *Generalized Advantage Estimation* (GAE).
2. **Normalisasi `VecNormalize`**: Observasi $S(t)$ dan imbalan $R(t)$ di-scale secara dinamis menggunakan *running mean* dan *running variance* dengan batas pemotongan (*clipping*) 10.0. Statistik ini disimpan ke `models/vec_normalize.pkl` dan di-load pada saat evaluasi inferensi untuk mencegah *distribution shift*.

   > ⚠️ **Catatan penting**: Statistik `VecNormalize` harus dibekukan (*frozen*) saat evaluasi inference. Me-load `vec_normalize.pkl` yang tersimpan selama training adalah **wajib**; menggunakan normalisasi live yang di-update oleh interaksi evaluasi akan menyebabkan *reward normalization drift* dan hasil evaluasi yang tidak valid secara komparatif.

---

### 4.5 Justifikasi Pemilihan Algoritma: Mengapa PPO?

Kontrol aeroponik merupakan masalah **kontrol kontinu** dengan ruang aksi $\mathbb{R}^3$ yang membutuhkan kebijakan kontrol presisi dan stabil. Berikut adalah analisis komparatif terhadap algoritma RL on-policy yang umum digunakan: **A2C**, **PPO**, dan **SAC**.

#### 4.5.1 Karakteristik Masalah Aeroponik

Sebelum memilih algoritma, penting untuk memahami karakteristik spesifik sistem aeroponik yang mempengaruhi kinerja RL:

| Karakteristik | Deskripsi | Dampak ke Algoritma |
|---------------|-----------|---------------------|
| **Tipe lingkungan** | Simulator fisiologis deterministik + sedikit stokastik | On-policy cocok; tidak butuh replay buffer |
| **Panjang episode** | 24 jam (timer-based, siklus misting ON/OFF) | Batch size besar lebih stabil |
| **Ruang aksi** | Kontinu, 3D ($D_{\text{mist}}$, $interval_{\text{sec}}$, $A_{\text{valve}}$) | Metode Actor-Critic natural |
| **Ruang status** | Kontinu, 10D di simulator (observasi agen); $T_{\text{root}}$ hanya estimasi internal untuk dinamika | Normalisasi diperlukan |
| **Biaya sampel** | Murah (simulator) | Efisiensi sampel tidak kritis |
| **Tingkat noise** | Rendah | Eksplorasi bisa manual/entropy |
| **Kendala keamanan** | pH, EC, H_in harus dalam rentang | Reward shaping lebih efektif |

#### 4.5.2 Perbandingan Algoritma RL

| Kriteria | A2C | PPO | SAC |
|----------|-----|-----|-----|
| **Tipe** | On-policy, sinkron | On-policy, clipped surrogate | Off-policy, actor-critic |
| **Batch size default** | 5-20 | 2048 | 256+ |
| **Efisiensi sampel** | Rendah | Sedang | Tinggi |
| **Stabilitas training** | Sedang | Tinggi | Sedang-Tinggi |
| **Sensitivitas hyperparameter** | Tinggi | Rendah | Sedang |
| **Eksplorasi** | Manual (`use_sde`, `ent_coef`) | Built-in (clipped objective + entropy) | Otomatis (max entropy) |
| **Replay buffer** | Tidak ada | Tidak ada | Ada |
| **Kecepatan konvergensi** | Lambat | Cepat | Sedang |
| **Kestabilan training pada reward multi-komponen** | ⚠️ Kurang | ✅ Ya | ⚠️ Overkill |
| **Cocok untuk kontrol kontinu** | ⚠️ Bisa | ✅ Disarankan | ✅ Terbaik |
| **Kemudahan implementasi** | Mudah | Mudah | Sedikit ribet |
| **Kebersihan akademis** | ⚠️ Memerlukan penjelasan tambahan | ✅ Jelas | ⚠️ Memerlukan penjelasan tambahan |

#### 4.5.3 Analisis A2C untuk Aeroponik

A2C dipilih pada iterasi awal karena kesederhanaan dan integrasi langsung dengan `stable-baselines3`. Namun, pengujian mengungkap beberapa kelemahan struktural untuk kasus ini:

1. **Batch size terlalu kecil**: `n_steps=20` menghasilkan batch size = 20 untuk single environment. Estimasi gradien menjadi sangat noisy, menyebabkan policy collapse ke local optimum (misalnya, agent belajar `D_mist ≈ 0` untuk menghindari penalty).

2. **Tidak ada clipping mechanism**: A2C melakukan policy update langsung tanpa pembatasan. Untuk continuous action space dengan reward function yang kompleks, ini berisiko menyebabkan perubahan policy yang terlalu besar antar update.

3. **Efisiensi sampel rendah**: A2C adalah on-policy algorithm yang tidak bisa reuse data lama. Untuk simulator aeroponik yang murah, ini bukan masalah besar, tapi mengurangi kecepatan convergence.

4. **Peringatan SB3**: Stable-Baselines3 secara eksplisit memperingatkan bahwa A2C dengan `MlpPolicy` sebaiknya dijalankan di CPU karena GPU utilization akan poor. Ini mengindikasikan bahwa A2C tidak memanfaatkan arsitektur modern yang efisien.

#### 4.5.4 Analisis SAC untuk Aeroponik

SAC (Soft Actor-Critic) adalah state-of-the-art untuk continuous control, tetapi memiliki beberapa kekurangan untuk kasus ini:

1. **Overkill untuk simulator**: SAC dirancang untuk sample-efficient learning pada environment dengan biaya tinggi (real robot, real-world interaction). Untuk simulator aeroponik yang murah dan cepat, keuntungan sample efficiency SAC tidak terasa signifikan.

2. **Kompleksitas hyperparameter**: SAC memiliki lebih banyak hyperparameter yang perlu di-tuning (`tau`, `ent_coef`, `target_update_interval`, dll.). Ini mempersulit reproducibility dan penjelasan dalam thesis.

3. **Inkonsistensi off-policy**: SAC menggunakan replay buffer yang menyimpan data dari policy lama. Untuk environment dengan reward function yang berubah seiring training (reward shaping), ini bisa menyebabkan inconsistenci dalam learning signal.

4. **Instabilitas training**: SAC terbukti kurang stabil untuk environment dengan deterministic dynamics seperti aeroponic simulator. Agent sering kali mengalami performance degradation di tengah training.

#### 4.5.5 Justifikasi Pemilihan PPO

Berdasarkan analisis di atas, **PPO dipilih sebagai algoritma utama** untuk sistem aeroponik dengan alasan berikut:

1. **Stabilitas training yang tinggi**: PPO menggunakan clipped surrogate objective yang membatasi perubahan policy antar update. Ini mencegah policy collapse dan memastikan convergence yang lebih predictable untuk continuous action space.

2. **Batch size besar**: `n_steps=4096` dengan single environment menghasilkan batch yang cukup besar untuk gradient estimate yang stabil. Ini krusial untuk reward function yang kompleks dengan multiple components.

3. **Robustness hyperparameter**: PPO kurang sensitif terhadap hyperparameter tuning dibanding A2C. Konfigurasi default dari SB3 RL Zoo sudah bekerja well untuk continuous control, memudahkan reproducibility.

4. **Konsistensi on-policy**: Seperti A2C, PPO adalah on-policy algorithm yang tidak menggunakan replay buffer. Ini cocok untuk simulator aeroponik yang deterministik dan murah, di mana data baru bisa di-generate cepat.

5. **Kemudahan justifikasi thesis**: PPO adalah algoritma yang lebih umum diakui dalam literature kontrol pertanian. Banyak paper precision agriculture menggunakan PPO untuk continuous control, memudahkan penempatan penelitian dalam konteks akademis.

6. **Efisiensi sampel yang seimbang**: PPO memiliki sample efficiency yang cukup baik untuk simulator aeroponik. Dengan 500,000 timesteps, PPO dapat mencapai convergence yang lebih baik dibanding A2C dengan budget yang sama.

7. **Entropy regularization built-in**: PPO secara natural mendorong exploration melalui entropy regularization dalam clipped objective. Ini mengurangi kebutuhan untuk tuning `ent_coef` secara manual.

#### 4.5.6 Konfigurasi Hyperparameter PPO

Berdasarkan SB3 RL Zoo, best practices untuk continuous control, dan perbaikan terkini:

| Hyperparameter | Nilai | Justifikasi |
|----------------|-------|-------------|
| `learning_rate` | 3e-4 → 1e-5 (linear schedule) | Default PPO; diikuti linear decay untuk fine-tuning di akhir training |
| `n_steps` | 4096 | Batch size besar untuk stabilitas gradien pada reward multi-komponen |
| `batch_size` | 128 | Mini-batch untuk penggunaan CPU yang efisien |
| `n_epochs` | 10 | Jumlah epoch per update; cukup untuk konvergensi |
| `gamma` | 0.995 | Episode 24 jam timer-based; diskon tinggi untuk reward jangka panjang |
| `ent_coef` | 0.05 (adaptive) | Eksplorasi lebih tinggi; diadaptasi secara dinamis berdasarkan entropy policy |
| `vf_coef` | 0.5 | Bobot value function loss; menyeimbangkan policy dan value learning |
| `max_grad_norm` | 1.0 | Clipping gradient untuk stabilitas training |
| `clip_range` | 0.1 | PPO clipping parameter; lebih konservatif untuk prevent policy collapse |
| `gae_lambda` | 0.95 | Lambda untuk Generalized Advantage Estimation |
| `device` | cpu | PPO dengan MlpPolicy lebih stabil di CPU |
| `tensorboard_log` | ./aeroponic_ppo_tensorboard/ | Melacak kurva training |
| `clip_obs` | 10.0 | Batas clipping observasi pada VecNormalize |
| `clip_reward` | 10.0 | Batas clipping reward pada VecNormalize untuk stabilisasi critic |

#### 4.5.7 Action Diversity Bonus

Untuk mencegah agent menempel di batas bawah action space ($D_{\text{mist}}=120$, $interval=360$, $A_{\text{valve}}=0$), ditambahkan diversity bonus berbasis history aksi terakhir:

- Jika $\text{std}(D_{\text{mist}}) > 10.0$: +2.0
- Jika $\text{std}(interval) > 20.0$: +1.0
- Jika pergantian $A_{\text{valve}} \ge 2$ kali: +0.5

Bonus ini:
- Mendorong eksplorasi durasi misting yang beragam di luar 120s
- Mendorong interval OFF yang bervariasi di luar 360s
- Mendorong penggunaan valve untuk memastikan agent memanfaatkan seluruh action space

| Metrik | A2C (50k timesteps) | A2C (500k timesteps) | PPO (500k timesteps) |
|--------|---------------------|----------------------|----------------------|
| **Rata-rata Reward** | ~5 | ~50-80 | ~100-150 |
| **L_root Akhir** | ~10 cm | ~15-20 cm | ~20-25 cm |
| **Aktivasi misting** | ~0% | ~20-30% | ~40-60% |
| **Stabilitas training** | Rendah | Sedang | Tinggi |
| **Episode konvergensi** | N/A | 500+ | 200-300 |

> \* Angka-angka di tabel ini merupakan **proyeksi heuristic** berdasarkan: (1) pola konvergensi umum PPO vs A2C untuk continuous control di SB3 RL Zoo, (2) literature reward scaling untuk kontrol pertanian, dan (3) asumsi bahwa reward komponen pertumbuhan dengan bobot 1500 menjadi sinyal dominan setelah ~200 episode. Ini bukan hasil eksperimen terkontrol dengan seeded runs.

### 4.6 Baseline Controllers

Untuk evaluasi komparatif, dua controller konvensional diimplementasikan sebagai baseline:

1. **Timer-Based Controller**: Mengeluarkan aksi misting dengan interval tetap setiap 30 menit, durasi 2 menit. Tidak ada adaptasi terhadap kondisi lingkungan. Parameter interval dan durasi diambil dari interval optimal Tunio et al. (2021).
2. **PID-Like Controller**: Menggunakan kontrol on/off dengan threshold $H_{\text{in}} < 85\%$ untuk memicu misting ON selama 2 menit, lalu OFF selama interval dihitung dari yang terakhir $H_{\text{in}}$ tercatat. Tidak ada integrasi/derivatif; hanya proporisional terhadap deviasi kelembaban.

Kedua baseline ini dirancang untuk menangkap performa kontrol tanpa pembelajaran, agar kontribusi PPO dapat diukur relatif terhadap solusi non-RL.

### 4.7 Protokol Evaluasi Inferensi & Pencegahan Reward Hacking
Untuk menjamin validitas ilmiah hasil evaluasi komparatif antara PPO, Timer-Based, dan PID-Like, diterapkan 3 protokol pengujian ketat:
1. **Un-normalization Reward (`norm_reward = False`)**: Saat evaluasi, statistik pemotong skalar `VecNormalize` dimatikan (`norm_reward = False`). Hal ini mencegah akumulasi skalar buatan (seperti *inflated reward* semu $+17,188$) dan memastikan imbalan kumulatif yang tercatat adalah **Physical Reward Unnormalized** yang apel-ke-apel dengan controller konvensional.
2. **Action Clipping Realistis**: Aksi raw continuous dari agen PPO di-klip ke rentang fisik aktuator: $\text{clip}(D_{\text{mist}}, 0, 300)$, $\text{clip}(interval_{\text{sec}}, 60, 3600)$, dan $\text{clip}(A_{\text{valve}}, 0, 1)$ sebelum diproses oleh simulator.
3. **Penyelarasan Kalibrasi Pendinginan Evaporatif ($0.3^\circ\text{C}/\text{langkah}$)**: Laju pendinginan evaporatif zona akar disesuaikan menjadi $-0.3^\circ\text{C}$ per langkah misting aktif, konsisten dengan bagian 3.2. Hal ini mencegah *over-cooling* ekstrem ke $10^\circ\text{C}$ dan memastikan dinamika fisiologis suhu $T_{\text{root}}$ berjalan konsisten dengan pertumbuhan akar riil.

---

## 📚 5. Kredit Riset & Referensi Literatur Ilmiah

Persamaan matematika, rentang parameter fisiologis, dan skenario dinamika pada simulator ini dikalibrasi berdasarkan publikasi ilmiah bereputasi berikut:

1. **Lakhiar, I. A., Gao, J., Syed, T. N., Chandio, F. A., & Buttar, N. A. (2018)**. *Aeroponics for agriculture: A review of recent research results*. **Information Processing in Agriculture**, 5(2), 245-256. https://doi.org/10.1016/j.inpa.2018.02.002
   * *Kontribusi*: Landasan teori hipoksia zona akar, pentingnya aerasi O₂, dan perancangan interval pengkabutan.
2. **Ritter, E., Angulo, B., Riga, P., Herrán, C., Relloso, J., & San Jose, M. (2001)**. *Comparison of hydroponic and aeroponic cultivation systems for the production of potato minitubers*. **Potato Research**, 44(2), 127-135.
   * *Kontribusi*: Data empiris laju pertumbuhan akar kentang (*Root Elongation Rate*) $1.0 - 2.0\text{ cm/hari}$.
3. **Tunio, M. H., Gao, J., Shaikh, S. A., Lakhiar, I. A., Qureshi, W. A., Solangi, K. A., & Chandio, F. A. (2021)**. *Potato growth and yield performance under aeroponic system with different atomization intervals*. **Circular Agricultural Economy**, 3(1), 1-10.
   * *Kontribusi*: Model dinamika kelembapan relatif ($H_{\text{in}}$) dan interval waktu misting optimal.
4. **Eldridge, B. M., Manzoni, L. R., Graham, C. A., Rodgers, B., Farmer, J. R., & Dodd, A. N. (2020)**. *Getting to the roots of aeroponic indoor farming*. **New Phytologist**, 228(4), 1183-1192.
   * *Kontribusi*: Fisiologi zona akar indoor farming & respons difusi oksigen pada akar tanaman.
5. **Tibbitts, T. W., Cao, W., & Wheeler, R. M. (2002)**. *Growth of potatoes for controlled environments*. **Advances in Space Research**, 14(11), 53-61.
   * *Kontribusi*: Rentang optimal $EC$ ($1.2 - 2.0\text{ mS/cm}$) dan $pH$ ($5.5 - 6.5$) untuk komoditas kentang.
