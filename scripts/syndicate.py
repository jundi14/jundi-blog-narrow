import os
import re
import json
import html
import mimetypes
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
import requests

RSS_PATH = './public/micro/index.xml'
STATE_FILE = './.syndicated-micro.json'
MAX_LENGTH = 300
MAX_IMAGES = 4
BSKY_PDS = 'https://bsky.social/xrpc'


def extract_images(raw_html):
    """Mengekstrak maksimal 4 URL gambar dan alt text dari tag <img>."""
    if not raw_html:
        return []
    images = []
    img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', raw_html, re.IGNORECASE)
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', raw_html, re.IGNORECASE):
        if len(images) >= MAX_IMAGES:
            break
        full_tag = match.group(0)
        src = match.group(1)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
        alt = alt_match.group(1) if alt_match else 'Foto microblog'
        if not any(img['src'] == src for img in images):
            images.append({'src': src, 'alt': alt})
    return images


def get_image_bytes(src):
    """Mencari file gambar di ./public, ./static, atau ./static/images/micro."""
    try:
        if src.startswith(('http://', 'https://')):
            parsed = urlparse(src)
            clean_path = unquote(parsed.path)
        else:
            clean_path = unquote(src)

        rel_path = clean_path.lstrip('/')
        file_name = os.path.basename(rel_path)

        candidate_paths = [
            os.path.join('./public', rel_path),
            os.path.join('./static', rel_path),
            os.path.join('./static/images/micro', file_name),
        ]

        for fpath in candidate_paths:
            if os.path.isfile(fpath):
                print(f"Mengambil gambar lokal dari: {fpath}")
                mime_type, _ = mimetypes.guess_type(fpath)
                with open(fpath, 'rb') as f:
                    return f.read(), (mime_type or 'image/jpeg')

        # Fallback: unduh jika gambar berada di URL eksternal
        if src.startswith(('http://', 'https://')):
            resp = requests.get(src, timeout=15)
            resp.raise_for_status()
            mime_type = resp.headers.get('Content-Type') or 'image/jpeg'
            return resp.content, mime_type

    except Exception as e:
        print(f"Melewati gambar ({src}): {e}")
    return None, None


def clean_html(raw_html):
    """Membersihkan tag HTML menjadi teks biasa."""
    if not raw_html:
        return ''
    text = re.sub(r'</p>', '\n\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def detect_facets(text):
    """Mendeteksi URL dan Hashtag secara otomatis menggunakan perhitungan byte UTF-8."""
    facets = []

    # 1. Deteksi Link URL (http:// atau https://)
    url_pattern = re.compile(r'https?://[^\s)\]>]+')
    for match in url_pattern.finditer(text):
        url = match.group(0).rstrip('.,;:!?')
        start_char = match.start()
        end_char = start_char + len(url)
        byte_start = len(text[:start_char].encode('utf-8'))
        byte_end = len(text[:end_char].encode('utf-8'))
        facets.append({
            'index': {'byteStart': byte_start, 'byteEnd': byte_end},
            'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': url}]
        })

    # 2. Deteksi Hashtag (#tag)
    tag_pattern = re.compile(r'(?<!\w)#([a-zA-Z0-9_]+)')
    for match in tag_pattern.finditer(text):
        full_tag = match.group(0)
        tag_name = match.group(1)
        start_char = match.start()
        end_char = start_char + len(full_tag)
        byte_start = len(text[:start_char].encode('utf-8'))
        byte_end = len(text[:end_char].encode('utf-8'))
        facets.append({
            'index': {'byteStart': byte_start, 'byteEnd': byte_end},
            'features': [{'$type': 'app.bsky.richtext.facet#tag', 'tag': tag_name}]
        })

    return facets


def main():
    if not os.path.exists(RSS_PATH):
        print(f"File {RSS_PATH} tidak ditemukan. Pastikan sudah menjalankan perintah 'hugo'.")
        return

    # 1. Baca riwayat sindikasi
    syndicated = []
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            syndicated = json.load(f)

    # 2. Parse XML
    tree = ET.parse(RSS_PATH)
    root = tree.getroot()
    channel = root.find('channel')
    if channel is None:
        return

    items = channel.findall('item')
    if not items:
        print("Belum ada item di dalam RSS microblog.")
        return

    # Inisialisasi pertama: simpan semua artikel lama agar tidak spam
    if len(syndicated) == 0:
        print("Inisialisasi pertama: mendata semua micro-post lama ke state file.")
        all_guids = []
        for item in items:
            guid = item.findtext('guid') or item.findtext('link')
            if guid:
                all_guids.append(guid.strip())
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_guids, f, indent=2)
        return

    # 3. Filter maksimal 3 micro-post baru (urutkan dari yang terlama)
    new_items = []
    for item in items:
        item_id = (item.findtext('guid') or item.findtext('link') or '').strip()
        if item_id and item_id not in syndicated:
            new_items.append(item)
    new_items = list(reversed(new_items[:3]))

    if not new_items:
        print("Tidak ada micro-post baru untuk dikirim ke Bluesky.")
        return

    # 4. Login ke Bluesky via XRPC
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_APP_PASSWORD')
    if not handle or not password:
        raise ValueError("Environment variable BSKY_HANDLE dan BSKY_APP_PASSWORD belum diisi!")

    session_resp = requests.post(
        f"{BSKY_PDS}/com.atproto.server.createSession",
        json={'identifier': handle, 'password': password},
        timeout=15
    )
    session_resp.raise_for_status()
    session_data = session_resp.json()
    access_jwt = session_data['accessJwt']
    did = session_data['did']
    auth_headers = {'Authorization': f'Bearer {access_jwt}'}

    # 5. Proses tiap micro-post
    for item in new_items:
        item_id = (item.findtext('guid') or item.findtext('link')).strip()
        link = (item.findtext('link') or '').strip()
        raw_html = item.findtext('description') or ''

        content = clean_html(raw_html)
        extracted_images = extract_images(raw_html)

        if not content and not extracted_images:
            continue

        post_text = content
        if len(content) > MAX_LENGTH:
            suffix = f"...\n\n{link}"
            allowed_len = MAX_LENGTH - len(suffix)
            post_text = content[:allowed_len].strip() + suffix

        # Unggah gambar jika ada
        embedded_images = []
        for img in extracted_images:
            img_bytes, mime_type = get_image_bytes(img['src'])
            if not img_bytes:
                continue

            if len(img_bytes) > 976000:
                print(f"Gambar {img['src']} melebihi batas 976KB Bluesky, dilewati.")
                continue

            blob_resp = requests.post(
                f"{BSKY_PDS}/com.atproto.repo.uploadBlob",
                headers={**auth_headers, 'Content-Type': mime_type},
                data=img_bytes,
                timeout=30
            )
            blob_resp.raise_for_status()
            blob_data = blob_resp.json().get('blob')

            embedded_images.append({
                'alt': img['alt'],
                'image': blob_data
            })

        # Susun record postingan Bluesky
        record = {
            '$type': 'app.bsky.feed.post',
            'text': post_text,
            'createdAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

        facets = detect_facets(post_text)
        if facets:
            record['facets'] = facets

        if embedded_images:
            record['embed'] = {
                '$type': 'app.bsky.embed.images',
                'images': embedded_images
            }

        post_resp = requests.post(
            f"{BSKY_PDS}/com.atproto.repo.createRecord",
            headers=auth_headers,
            json={
                'repo': did,
                'collection': 'app.bsky.feed.post',
                'record': record
            },
            timeout=15
        )
        post_resp.raise_for_status()
        print(f"Terkirim ke Bluesky ({len(embedded_images)} gambar): {link}")
        syndicated.append(item_id)

    # 6. Simpan state terbaru
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(syndicated, f, indent=2)


if __name__ == '__main__':
    main()