import os
import io
import re
import json
import html
import mimetypes
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
import requests
from PIL import Image

RSS_PATH = './public/micro/index.xml'
STATE_FILE = './.syndicated-micro.json'
MAX_LENGTH = 300
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 950000  # Di bawah batas 976 KB Bluesky
BSKY_PDS = 'https://bsky.social/xrpc'


def extract_images(raw_html):
    """Mengekstrak maksimal 4 URL gambar dan alt text setelah unescape HTML."""
    if not raw_html:
        return []
    # Unescape terlebih dahulu agar &lt;img src=&#34;...&#34;&gt; terbaca normal
    decoded_html = html.unescape(raw_html)
    images = []

    for match in re.finditer(r'<img[^>]+src=["\']?([^"\'\s>]+)["\']?[^>]*>', decoded_html, re.IGNORECASE):
        if len(images) >= MAX_IMAGES:
            break
        full_tag = match.group(0)
        src = match.group(1)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
        alt = alt_match.group(1) if alt_match else 'Foto microblog'
        if not any(img['src'] == src for img in images):
            images.append({'src': src, 'alt': alt})
    return images


def compress_image_if_needed(img_bytes, mime_type):
    """Mengompresi gambar secara otomatis jika ukurannya melebihi batas Bluesky."""
    if len(img_bytes) <= MAX_IMAGE_BYTES:
        return img_bytes, mime_type

    print(f"Ukuran gambar ({len(img_bytes)} bytes) > 950KB, mengompresi otomatis...")
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Kecilkan resolusi maksimal ke 1920px jika terlalu besar
    img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)

    for quality in [85, 75, 65, 50]:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        compressed = buf.getvalue()
        if len(compressed) <= MAX_IMAGE_BYTES:
            print(f"Berhasil dikompresi menjadi {len(compressed)} bytes (quality={quality}).")
            return compressed, 'image/jpeg'

    return buf.getvalue(), 'image/jpeg'


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
                    return compress_image_if_needed(f.read(), mime_type or 'image/jpeg')

        if src.startswith(('http://', 'https://')):
            print(f"Mengunduh gambar dari URL: {src}")
            resp = requests.get(src, timeout=15)
            resp.raise_for_status()
            mime_type = resp.headers.get('Content-Type') or 'image/jpeg'
            return compress_image_if_needed(resp.content, mime_type)

        print(f"File gambar tidak ditemukan di lokal untuk path: {src} (dicek: {candidate_paths})")
    except Exception as e:
        print(f"Melewati gambar ({src}): {e}")
    return None, None


def clean_html(raw_html):
    """Membersihkan tag HTML menjadi teks biasa."""
    if not raw_html:
        return ''
    text = html.unescape(raw_html)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def detect_facets(text):
    """Mendeteksi URL dan Hashtag secara otomatis."""
    facets = []
    for match in re.finditer(r'https?://[^\s)\]>]+', text):
        url = match.group(0).rstrip('.,;:!?')
        start_char = match.start()
        end_char = start_char + len(url)
        facets.append({
            'index': {
                'byteStart': len(text[:start_char].encode('utf-8')),
                'byteEnd': len(text[:end_char].encode('utf-8'))
            },
            'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': url}]
        })

    for match in re.finditer(r'(?<!\w)#([a-zA-Z0-9_]+)', text):
        full_tag = match.group(0)
        tag_name = match.group(1)
        start_char = match.start()
        end_char = start_char + len(full_tag)
        facets.append({
            'index': {
                'byteStart': len(text[:start_char].encode('utf-8')),
                'byteEnd': len(text[:end_char].encode('utf-8'))
            },
            'features': [{'$type': 'app.bsky.richtext.facet#tag', 'tag': tag_name}]
        })
    return facets


def main():
    if not os.path.exists(RSS_PATH):
        print(f"File {RSS_PATH} tidak ditemukan.")
        return

    syndicated = []
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            syndicated = json.load(f)

    tree = ET.parse(RSS_PATH)
    channel = tree.getroot().find('channel')
    if channel is None:
        return

    items = channel.findall('item')
    if not items:
        print("Belum ada item di dalam RSS microblog.")
        return

    if len(syndicated) == 0:
        print("Inisialisasi pertama: mendata semua micro-post lama ke state file.")
        all_guids = [
            (item.findtext('guid') or item.findtext('link')).strip()
            for item in items if (item.findtext('guid') or item.findtext('link'))
        ]
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_guids, f, indent=2)
        return

    new_items = []
    for item in items:
        item_id = (item.findtext('guid') or item.findtext('link') or '').strip()
        if item_id and item_id not in syndicated:
            new_items.append(item)
    new_items = list(reversed(new_items[:3]))

    if not new_items:
        print("Tidak ada micro-post baru untuk dikirim ke Bluesky.")
        return

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
    auth_headers = {'Authorization': f"Bearer {session_data['accessJwt']}"}
    did = session_data['did']

    for item in new_items:
        item_id = (item.findtext('guid') or item.findtext('link')).strip()
        link = (item.findtext('link') or '').strip()
        raw_html = item.findtext('description') or ''

        content = clean_html(raw_html)
        extracted_images = extract_images(raw_html)
        print(f"Memproses {link} -> Ditemukan {len(extracted_images)} tag gambar di RSS.")

        if not content and not extracted_images:
            continue

        post_text = content
        if len(content) > MAX_LENGTH:
            suffix = f"...\n\n{link}"
            allowed_len = MAX_LENGTH - len(suffix)
            post_text = content[:allowed_len].strip() + suffix

        embedded_images = []
        for img in extracted_images:
            img_bytes, mime_type = get_image_bytes(img['src'])
            if not img_bytes:
                continue

            blob_resp = requests.post(
                f"{BSKY_PDS}/com.atproto.repo.uploadBlob",
                headers={**auth_headers, 'Content-Type': mime_type},
                data=img_bytes,
                timeout=30
            )
            blob_resp.raise_for_status()
            embedded_images.append({
                'alt': img['alt'],
                'image': blob_resp.json().get('blob')
            })

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
            json={'repo': did, 'collection': 'app.bsky.feed.post', 'record': record},
            timeout=15
        )
        post_resp.raise_for_status()
        print(f"Terkirim ke Bluesky ({len(embedded_images)} gambar): {link}")
        syndicated.append(item_id)

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(syndicated, f, indent=2)


if __name__ == '__main__':
    main()