import { BskyAgent, RichText } from '@atproto/api';
import Parser from 'rss-parser';
import fs from 'fs';

const RSS_URL = 'https://jundi.web.id/micro/index.xml';
const CACHE_FILE = './blueskyfeedbot/cache.json';

async function run() {
  const parser = new Parser();
  const feed = await parser.parseURL(RSS_URL);

  // 1. Baca riwayat postingan (Cache) agar tidak memposting ulang yang lama
  let cache = [];
  if (fs.existsSync(CACHE_FILE)) {
    try {
      cache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
    } catch (e) {
      cache = [];
    }
  }

  // Ambil maksimal 3 item terbaru untuk diproses dari yang paling lama ke baru
  const items = feed.items.slice(0, 3).reverse();
  const newItems = items.filter(item => !cache.includes(item.guid || item.link));

  if (newItems.length === 0) {
    console.log('Tidak ada postingan Micro baru.');
    return;
  }

  // 2. Login ke Bluesky
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({
    identifier: process.env.BSKY_USERNAME,
    password: process.env.BSKY_PASSWORD,
  });

  // 3. Proses setiap postingan baru
  for (const item of newItems) {
    const text = (item.contentSnippet || item.content || '').trim();
    
    // Deteksi otomatis jika ada link atau mention di dalam teks
    const rt = new RichText({ text });
    await rt.detectFacets(agent);

    const postRecord = {
      $type: 'app.bsky.feed.post',
      text: rt.text,
      facets: rt.facets,
      createdAt: new Date().toISOString(),
    };

// 4. Cek apakah ada gambar di <enclosure>
    if (item.enclosure && item.enclosure.url) {
      try {
        console.log(`Mengunduh gambar: ${item.enclosure.url}`);
        const imgRes = await fetch(item.enclosure.url);
        if (imgRes.ok) {
          const arrayBuffer = await imgRes.arrayBuffer();
          let buffer = Buffer.from(arrayBuffer);

          // Kompres otomatis ke JPEG di bawah 900KB agar tidak ditolak Bluesky (batas 976KB)
          buffer = await sharp(buffer)
            .resize({ width: 1600, withoutEnlargement: true })
            .jpeg({ quality: 80 })
            .toBuffer();

          // Unggah gambar ke server Bluesky
          const { data } = await agent.uploadBlob(buffer, { encoding: 'image/jpeg' });
          
          // Sematkan gambar ke dalam postingan
          postRecord.embed = {
            $type: 'app.bsky.embed.images',
            images: [
              {
                alt: item.title || 'Gambar Microblog',
                image: data.blob,
              },
            ],
          };
          console.log('Gambar berhasil diunggah ke Bluesky.');
        } else {
          console.error(`Gagal mengambil gambar, status HTTP: ${imgRes.status}`);
        }
      } catch (err) {
        console.error('Gagal mengunggah gambar, lanjut memposting teks saja:', err);
      }
    }

    // 5. Kirim ke Bluesky dan simpan ke Cache
    await agent.post(postRecord);
    console.log(`Berhasil memposting: ${item.title}`);
    cache.push(item.guid || item.link);
  }

  // 6. Perbarui file Cache
  fs.mkdirSync('./blueskyfeedbot', { recursive: true });
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2));
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});