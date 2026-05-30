---
title: Secure Header di Netlify
slug: Secure Header di Netlify
description: Memberikan tingkat perlindungan yang besar dan penting bagi situs untuk menerapkannya
categories: Blogging
date: 2022-12-18
tags:
aliases: '/posts/blogging/secure-header-di-netlify/'
showComments: true
showTableOfContents: false
---

Apa itu Security header?

HTTP security header adalah bagian dari header ini dan berfungsi melindungi website dari ancaman

Seperti clickjacking, cross-site scripting, brute force, dan lain sebagainya.

Karena itu, kita harus tahu lebih banyak seperti apa fungsi HTTP security header untuk melindungi websitemu

Jika situs statis kamu di deploy menggunakan netlify tambahkan kode dibawah ini di pengaturan **netlify.toml**

Pengaturan ini dapat meningkatkan penggunaan header berbasis keamanan di seluruh web.

```bash
[[headers]]
      for = "/*"
      [headers.values]
        Content-Security-Policy = "default-src 'self'; img-src *; frame-ancestors 'none'"
        Referrer-Policy = "same-origin"
        Strict-Transport-Security = "max-age=63072000; includeSubdomains; preload"
        X-Content-Type-Options = "nosniff"
        X-Frame-Options = "DENY"
        X-XSS-Protection = "1; mode=block"
```

Silahkan cek website statis kamu pada situs [security headers](https://securityheaders.com/)

Jika kamu sudah menerapkan kode diatas maka kamu akan mendapatkan "nilai" yang bagus yang sebelumnya mendapat raport merah.

![](./pengecekan-http-header-a.png)

Header respons HTTP yang dianalisis situs ini memberikan tingkat perlindungan yang sangat besar dan penting bagi situs untuk menerapkannya.

_Note: Efek yang dihasilkan pada website saya adalah hilangnya kolom komentar disqus dan link donasi_ 😁

---

#### Sumber :

1. [https://idwebhost.com/blog/cara-menambahkan-https-di-wordpress/](https://idwebhost.com/blog/cara-menambahkan-https-di-wordpress/ 'https://idwebhost.com/blog/cara-menambahkan-https-di-wordpress/')
2. [https://ttntm.me/notes#18](https://ttntm.me/notes#18 'https://ttntm.me/notes#18')
