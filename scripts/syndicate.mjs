import fs from 'fs';
import path from 'path';
import { XMLParser } from 'fast-xml-parser';
import { BskyAgent, RichText } from '@atproto/api';

const RSS_PATH = './public/micro/index.xml';
const STATE_FILE = './.syndicated-micro.json';
const MAX_LENGTH = 300; // Batas maksimal karakter Bluesky
const MAX_IMAGES = 4;   // Batas maksimal gambar per post di Bluesky

// 1. Fungsi mengekstrak URL dan Alt Text gambar dari tag <img> di RSS
function extractImages(html) {
  if (!html) return [];
  const images = [];
  const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
  let match;

  while ((match = imgRegex.exec(html)) !== null && images.length < MAX_IMAGES) {
    const fullTag = match[0];
    const src = match[1];
    const altMatch = fullTag.match(/alt=["']([^"']*)["']/i);
    const alt = altMatch ? altMatch[1] : '';

    // Hindari duplikasi gambar yang sama dalam satu post
    if (!images.some(img => img.src === src)) {
      images.push({ src, alt });
    }
  }
  return images;
}

// 2. Fungsi menentukan MIME type berdasarkan ekstensi file
function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.png') return 'image/png';
  if (ext === '.webp') return 'image/webp';
  if (ext === '.gif') return 'image/gif';
  return 'image/jpeg';
}

// 3. Fungsi membaca file gambar dari ./public, ./static, atau ./static/images/micro
async function getImageBuffer(src) {
  try {
    let cleanPath = src;

    // Jika src berupa URL penuh, ambil pathname-nya saja
    if (src.startsWith('http://') || src.startsWith('https://')) {
      const urlObj = new URL(src);
      cleanPath = decodeURIComponent(urlObj.pathname);
    } else {
      cleanPath = decodeURIComponent(src);
    }

    const relativePath = cleanPath.replace(/^\/+/, '');
    const fileName = path.basename(relativePath);

    // Urutan lokasi pencarian gambar di repositori lokal
    const candidatePaths = [
      path.join('./public', relativePath),          // 1. Cek di ./public/images/micro/...
      path.join('./static', relativePath),          // 2. Cek di ./static/images/micro/...
      path.join('./static/images/micro', fileName), // 3. Cek nama file langsung di ./static/images/micro/
    ];

    for (const filePath of candidatePaths) {
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        console.log(`Mengambil gambar lokal dari: ${filePath}`);
        return {
          buffer: fs.readFileSync(filePath),
          mimeType: getMimeType(filePath),
        };
      }
    }

    // Fallback: Unduh via jaringan jika gambar di-host di luar repositori
    if (src.startsWith('http://') || src.startsWith('https://')) {
      const res = await fetch(src);
      if (!res.ok) throw new Error(`Gagal mengunduh ${src}: ${res.statusText}`);
      const arrayBuffer = await res.arrayBuffer();
      return {
        buffer: Buffer.from(arrayBuffer),
        mimeType: res.headers.get('content-type') || getMimeType(src),
      };
    }
  } catch (err) {
    console.warn(`Melewati gambar (${src}):`, err.message);
  }
  return null;
}

// 4. Fungsi membersihkan tag HTML menjadi teks biasa untuk status Bluesky
function cleanHtml(html) {
  if (!html) return '';
  return html
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]*>?/gm, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// 5. Fungsi Utama
async function run() {
  if (!fs.existsSync(RSS_PATH)) {
    console.log(`File ${RSS_PATH} tidak ditemukan. Pastikan section 'micro' menghasilkan RSS.`);
    return;
  }

  // Baca riwayat sindikasi sebelumnya
  let syndicated = [];
  if (fs.existsSync(STATE_FILE)) {
    syndicated = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  }

  // Parse XML dari ./public/micro/index.xml
  const xmlData = fs.readFileSync(RSS_PATH, 'utf-8');
  const parser = new XMLParser();
  const feed = parser.parse(xmlData);

  const rawItems = feed.rss?.channel?.item;
  if (!rawItems) {
    console.log('Belum ada item di dalam RSS microblog.');
    return;
  }
  const items = Array.isArray(rawItems) ? rawItems : [rawItems];

  // Inisialisasi pertama: simpan semua post lama agar tidak kena spam ke Bluesky
  if (syndicated.length === 0) {
    console.log('Inisialisasi pertama: mendata semua micro-post lama ke state file.');
    const allGuids = items.map(item => item.guid || item.link);
    fs.writeFileSync(STATE_FILE, JSON.stringify(allGuids, null, 2));
    return;
  }

  // Filter micro-post baru (maksimal 3 post sekali jalan, urut dari yang terlama)
  const newItems = items
    .filter(item => !syndicated.includes(item.guid || item.link))
    .slice(0, 3)
    .reverse();

  if (newItems.length === 0) {
    console.log('Tidak ada micro-post baru untuk dikirim ke Bluesky.');
    return;
  }

  // Login ke Bluesky
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({
    identifier: process.env.BSKY_HANDLE,
    password: process.env.BSKY_APP_PASSWORD,
  });

  // Proses pengiriman tiap micro-post
  for (const item of newItems) {
    const id = item.guid || item.link;
    const link = item.link;
    const rawHtml = item.description || '';

    const content = cleanHtml(rawHtml);
    const extractedImages = extractImages(rawHtml);

    // Lewati jika postingan kosong tanpa teks dan tanpa gambar
    if (!content && extractedImages.length === 0) continue;

    let postText = content;
    if (content.length > MAX_LENGTH) {
      const suffix = `...\n\n${link}`;
      const allowedLength = MAX_LENGTH - suffix.length;
      postText = content.substring(0, allowedLength).trim() + suffix;
    }

    const rt = new RichText({ text: postText });
    await rt.detectFacets(agent); // Aktifkan link, mention, dan hashtag otomatis

    // Unggah gambar ke Bluesky jika ada
    const embeddedImages = [];
    for (const img of extractedImages) {
      const imgData = await getImageBuffer(img.src);
      if (!imgData) continue;

      // Batas ukuran blob gambar Bluesky (~976 KB)
      if (imgData.buffer.byteLength > 976000) {
        console.warn(`Gambar ${img.src} melebihi batas 976KB Bluesky, dilewati.`);
        continue;
      }

      const uploadRes = await agent.uploadBlob(imgData.buffer, {
        encoding: imgData.mimeType,
      });

      embeddedImages.push({
        alt: img.alt || 'Foto microblog',
        image: uploadRes.data.blob,
      });
    }

    // Susun payload post
    const postPayload = {
      text: rt.text,
      facets: rt.facets,
      createdAt: new Date().toISOString(),
    };

    if (embeddedImages.length > 0) {
      postPayload.embed = {
        $type: 'app.bsky.embed.images',
        images: embeddedImages,
      };
    }

    await agent.post(postPayload);
    console.log(`Terkirim ke Bluesky (${embeddedImages.length} gambar): ${link}`);
    syndicated.push(id);
  }

  // Simpan state terbaru ke .syndicated-micro.json
  fs.writeFileSync(STATE_FILE, JSON.stringify(syndicated, null, 2));
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
