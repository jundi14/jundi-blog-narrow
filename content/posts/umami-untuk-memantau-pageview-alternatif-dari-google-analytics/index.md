---
title: Umami, Alternatif dari Google Analitik yang Lebih Cepat dan Sederhana
slug: Umami Alternatif dari Google Analitik
description: Umami, alternatif google analitik yang sederhana, lebih ringan dan cepat serta tidak membebani server karena size yang lebih kecil.
categories: Blogging
date: 2023-08-24
tags:
showComments: true
showTableOfContents: true
draft: false
---

Sebenarnya ada banyak sekali aplikasi untuk memantau pageviews atau visitor dari website yang kita miliki, tetapi karena yang paling dikenal oleh kebanyakan dari kita adalah google. Maka Google Analytic lah pilihannya.

Kita tidak asing dengan aplikasi itu.

Kalau kita tengok menu pada google analitik ada banyak sekali menu yang membingungkan untuk pemula dan lebih banyak yang tidak kita gunakan.

Bisa jadi untuk pengguna tingkat lanjut akan dibutuhkan untuk menunjang bisnis, misalnya.

Tapi karena kebutuhan kita hanya melihat pageviews, visitor, diakses di perangkat apa saja.

Maka Google Analytic terlalu kompleks dilihat dari fiturnya dan sedikit membebani server shared hosting dengan kapasitas yang kecil.

Ada alternatif pengganti google analitik yaitu umami.
Umami fokus pada kesederhanaan, tampilan yang lebih _user-friendly_ dan ringan sehingga lebih cepat pastinya.

![ Contoh Tampilan Analitik Umami](./analitik-umami.png 'Tampilan Analitik Umami')

Nah bagaimana cara menggunakan umami ?

Ada beberapa langkah yang harus diikuti untuk membuat akun umami, sedikit merepotkan untuk user google analitik yang sudah terintegrasi dengan layanan google lainnya.

Tapi mengingat kelebihan yang dimiliki oleh umami ini cukup powerfull, maka kita akan coba untuk menginstalnya.

Ada beberapa syarat untuk menginstall umami.

## Prasyarat Sebelum Menginstall Umami

### Membuat Akun Github

Buatlah akun [github](https://github.com/) terlebih dahulu dengan menggunakan email

![Sign Up Github](./screenshot-sign-up-github.png 'Sign Up Github')
![Sign In Github](./screenshot-sign-in-github.png 'Sign In Github')

Lalu verifikasi email untuk login ke akun github.

Jika sudah punya akun github, bisa skip langkah ini.

### Membuat Akun Supabase

Ini juga alternatif dari firebase yang juga milik si raksasa Google.
Bedanya supabase ini Open Source.

Kamu bisa sign up [Supabase](https://supabase.com) menggunakan email atau bisa langsung menggunakan akun github kamu, lalu nanti akan langsung masuk ke dashboard supabase.

![Sign Up Supabase](./login-supabase.png 'Halaman Sign Up Supabase')

![Sign Up Supabase Via Github](./login-via-github.png 'Sign Up Menggunakan Akun Github')

Setelah kamu telah melakukan pendaftaran dan login ke halaman supabase, berikutnya kamu harus membuat nama organisasi, silahkan isi sesukamu tidak diharuskan organisasi tertentu.

Karena saya telah membuat organisasi, maka saya langsung ke tahapan membuat proyek, isi saja sesuai selera, setelah itu buatlah password untuk databasenya, gunakan saja **Generate a Password** agar dibuatkan password yang kuat.

Lalu simpan di note password yang telah dibuat.

Untuk _Region_ dan _Pricing Plan_, ikuti saja sesuai dengan gambar.

![Membuat Proyek di Supabase](./membuat-proyek-supabase.png 'Membuat Proyek di Supabase')

![Proyek berhasil](./proyek-berhasil.png)

Setelah sukses membuat projek, lalu pilih proyeknya lalu klik **project setting** yang ber-icon gear di bagian menu sebelah kiri paling bawah.

![Setting Database](./setting-database.png 'Setting Database')

Lalu pilih database dan pada **Connection String** lalu copy URL yang tampil. Simpan salinan URL ke note.

### Membuat Akun Vercel

Ini adalah tempat kamu mendeploy aplikasi dari umami yang nanti akan kita gunakan.

Buatlah akun vercel menggunakan email ataupun akun github yang sudah kita buat pada tahap awal.

![Login Vercel](./login-vercel.png)

Lalu buatlah sebuat team, dengan sebuah nama yang kamu sukai.

---

## Menginstal Umami

Ya, inilah tahapan inti, yaitu memasang umami.

Yang perlu kita lakukan adalah mengakses halaman ini untuk menginstal umami di vercel.

![Running on Vercel](./running-on-vercel.png)

Lalu pada Setup klik **Deploy**

Kemudian halaman akan dialihkan ke vercel dan silahkan masukkan nama direktori yang kamu inginkan lalu klik **Create**.

![Buat Repository](./masukkan-repository.png)

Setelah itu masukkan URL di bagian **Value** yang kita dapat pada tahapan membuat akun supabase tadi, lalu ganti :

```
[YOUR PASSWORD]
```

dengan password yang kita **Generate Password** di tahapan supabase juga.

![Deploy Umami](./deploy-umami.png)

Setelah itu klik deploy!
Tunggu beberapa saat...

Taraa.!

![Halaman sukses deploy umami](./laman-sukses-vercel.png)

Lalu bisa kamu klik **Visit** pada halaman dashboard vercel.

Yap, Inilah halaman login umami.
Mudah bukan? 🤭

---

## Setting Umami

### Merubah Password Umami

Setelah tahapan diatas selesai silahkan login dengan username dan password default berikut :

```
Username    : admin
Password    : umami
```

Silahkan ubah terlebih dahulu password dan juga usernamenya pada menu **setting** kemudian pilih **users**.

Yang terpenting jangan sama dengan password default umami.

![Mengganti username dan password umami](./ganti-password-umami.png)

### Menambahkan Website di Umami

Cara menambahkan website ke umami adalah dengan cara pilih setting lalu pilih website, lalu pilih tambahkan, masukkan nama dan url website kamu dan klik OK.

Lalu klik edit, pilihlah tracking code lalu salin dan tambahkan kode tersebut diantara

```
</head>...</head>
```

Pada website kamu

![Menambahkan Website](./setting-website.png)

Dan sekarang website kamu sudah terpasang analitik dari umami tinggal akses dashboard dan akan terlihat semua statistiknya.😁

Jika masih ada yang kurang dimengerti bisa tanyakan di kolom komentar.
