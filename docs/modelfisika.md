# Model Fisika — Simulator Aeroponik

## 1. Update Panjang Akar ($L_{\text{root}}$)

### Sumber kode
`control-model-training/aeroponic_simulator.py` — bagian `_update_state_dynamics()`, blok capture setiap 3 jam.

### Frekuensi update
Panjang akar tidak diperbarui setiap menit. Update hanya terjadi pada **titik capture** setiap 3 jam sejak $t=0$, yaitu pada $t = 0, 3\text{h}, 6\text{h}, 9\text{h}, \dots$.

### Rumus logistic growth

$$
\Delta L_{\text{root}} = r_{\text{step}} \cdot 180 \cdot L_{\text{root}} \cdot \left(1 - \frac{L_{\text{root}}}{K}\right) \cdot f_{\text{lim}} \cdot d_{\text{day}}
$$

$$
L_{\text{root, baru}} = \max(0,\; L_{\text{root, lama}} + \Delta L_{\text{root}})
$$

### Parameter

| Simbol | Nilai | Satuan | Keterangan |
|--------|-------|--------|------------|
| $r_{\text{step}}$ | $1.5 \times 10^{-5}$ | cm/min | Laju pertumbuhan akar spesifik per menit |
| $180$ | — | menit | Interval capture (3 jam = 180 menit) |
| $L_{\text{root}}$ | — | cm | Panjang akar saat capture sebelumnya |
| $K$ | $300$ | cm | Kapasitas pembawa (carrying capacity) |
| $f_{\text{lim}}$ | $[0, 1]$ | — | Faktor pembatas lingkungan (limiting factor) |
| $d_{\text{day}}$ | $1.2$ (siang) / $0.6$ (malam) | — | Multiplier periode siang/malam |

### Faktor pembatas lingkungan ($f_{\text{lim}}$)

$$f_{\text{lim}} = \min(f_{H_{\text{in}}},\; f_{O_2},\; f_T)$$

#### a. Faktor kelembaban ($f_{H_{\text{in}}}$)

$$
f_{H_{\text{in}}} = \min\left(1.0,\; \frac{H_{\text{in}}}{80}\right)
$$

$H_{\text{in}}$ dalam % RH. Batas optimal = 80%.

#### b. Faktor oksigen ($f_{O_2}$)

$$
f_{O_2} = \max\left(0.0,\; 1.0 - 0.12 \cdot \max(0,\; T_{\text{continuous}} - 3)\right)
$$

$T_{\text{continuous}}$ = lamanya misting menyala terus-menerus tanpa jeda (menit). Oksigen menurun ketika misting ON terlalu lama tanpaOFF.

#### c. Faktor suhu ($f_T$)

$$
f_T =
\begin{cases}
1.0 & 18 \leq T_{\text{in}} \leq 28 \\
\max(0.3,\; 1.0 - (18 - T_{\text{in}}) \cdot 0.1) & T_{\text{in}} < 18 \\
\max(0.3,\; 1.0 - (T_{\text{in}} - 28) \cdot 0.15) & T_{\text{in}} > 28
\end{cases}
$$

$T_{\text{in}}$ dalam °C. Rentang optimal = 18–28 °C. Di luar rentang, $f_T$ turun minimal ke 0.3.

### Multiplier siang/malam ($d_{\text{day}}$)

$$
d_{\text{day}} =
\begin{cases}
1.2 & I_{\text{day}} = 1.0 \text{ (siang)} \\
0.6 & I_{\text{day}} = 0.0 \text{ (malam)}
\end{cases}
$$

### Kondisi kematian tanaman

Jika tanaman mati atau $U_{\text{status}} \leq 0$:

$$
\Delta L_{\text{root}} = -0.5 \cdot L_{\text{root, lama}}
$$

Artinya akar menyusut 50% dari panjang sebelumnya.

### Probabilitas kematian

$$
P_{\text{death}} = \max(0,\; 1 - f_{\text{lim}})^3 \cdot 0.05
$$

Jika $\text{random()} < P_{\text{death}}$, tanaman dianggap mati pada capture tersebut.

---

## 2. Interpretasi

- Model ini merupakan **pertumbuhan logistic** yang dibatasi oleh faktor lingkungan (suhu, kelembaban, oksigen).
- $K=300$ cm menandakan akar tidak bisa tumbuh tanpa batas — sesuai karakteristik biologis tanaman.
- $r_{\text{step}}$ sangat kecil karena update hanya setiap 3 jam, sehingga total growth per hari tetap realistis untuk aeroponik.
- Faktor siang/malam ($d_{\text{day}}$) menggambarkan fotosintesis: akar tumbuh lebih cepat saat ada cahaya.
- Jika salah satu faktor lingkungan sangat buruk, $f_{\text{lim}} \to 0$ dan pertumbuhan terhenti; jika terlalu buruk, tanaman bisa mati.
