const fs = require('fs');
const path = require('path');

// Cek argumen --force dari terminal
const DRY_RUN = !process.argv.includes('--force');

const postsDir = path.join(process.cwd(), 'content/posts');

if (!fs.existsSync(postsDir)) {
  console.log('Folder content/posts tidak ditemukan.');
  process.exit(0);
}

console.log(DRY_RUN ? '🔍 Mode DRY-RUN (tidak ada yang dihapus)' : '🗑️  Mode HAPUS');
console.log('-----------------------------------');

for (const folder of fs.readdirSync(postsDir)) {
  const folderPath = path.join(postsDir, folder);
  if (!fs.statSync(folderPath).isDirectory()) continue;

  const files = fs.readdirSync(folderPath);
  const hasContentFile = files.some(file => /^_?index\.(md|html)$/i.test(file));

  if (!hasContentFile) {
    console.log(`${DRY_RUN ? '[DRY-RUN]' : '[HAPUS]'} Orphan ditemukan pada postingan: ${folder}`);
    if (!DRY_RUN) {
      fs.rmSync(folderPath, { recursive: true, force: true });
    }
  }
}

console.log('-----------------------------------');
console.log(DRY_RUN ? '✅ Selesai. Jalankan dengan --force untuk hapus.' : '✅ Selesai. Semua orphan telah dihapus.');