import requests
from bs4 import BeautifulSoup
import re
import json
import base64
import os
import csv

class OtakudesuScraper:
    BASE_URL = "https://otakudesu.best"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.local_index = self._load_index()

    def _load_index(self):
        index = {}
        try:
            index_path = os.path.join("data", "index.csv")
            if os.path.exists(index_path):
                with open(index_path, "r", newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('url')
                        seq = row.get('seq')
                        if url and seq:
                            index[url] = seq
            else:
                print(f"{index_path} not found, falling back to live requests only.")
        except Exception as e:
            print(f"Error loading index: {e}")
        return index

    def _find_local_file(self, url):
        # Strip query parameters for lookup if exact match fails
        seq = self.local_index.get(url)

        if not seq:
             url_no_query = url.split('?')[0]
             # This simple check is flawed if index keys have query params, but some might not.
             # Actually, let's just trust the index keys.
             # If exact match fails, we can try to iterate? No, too slow.
             pass

        if seq:
            seq_padded = seq.zfill(5)

            domain = url.split("://")[1].split("/")[0]
            search_path = os.path.join("data", domain)

            if os.path.exists(search_path):
                for item in os.listdir(search_path):
                    if item.startswith(seq_padded):
                        dir_path = os.path.join(search_path, item)
                        for file in os.listdir(dir_path):
                            if file.startswith("04_res_body"):
                                return os.path.join(dir_path, file)
        return None

    def _get_soup(self, url):
        # Try local first
        local_file = self._find_local_file(url)
        if local_file:
            try:
                with open(local_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return BeautifulSoup(content, "lxml")
            except Exception as e:
                print(f"Error reading local file {local_file}: {e}")

        # Fallback to live
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, "lxml")
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def get_home(self):
        soup = self._get_soup(self.BASE_URL + "/") # Ensure trailing slash to match index.csv likely
        if not soup:
            soup = self._get_soup(self.BASE_URL) # Try without if failed

        if not soup:
            return {"ongoing": [], "complete": []}

        ongoing = []
        venz = soup.find('div', class_='venz')
        if venz:
             for item in venz.find_all('li'):
                detpost = item.find('div', class_='detpost')
                thumb = item.find('div', class_='thumb')
                if detpost and thumb:
                    ep = detpost.find('div', class_='epz').get_text(strip=True) if detpost.find('div', class_='epz') else ""
                    day = detpost.find('div', class_='epztipe').get_text(strip=True) if detpost.find('div', class_='epztipe') else ""
                    date = detpost.find('div', class_='newnime').get_text(strip=True) if detpost.find('div', class_='newnime') else ""

                    link_tag = thumb.find('a')
                    img_tag = thumb.find('img')
                    title_tag = thumb.find('h2', class_='jdlflm')

                    if link_tag and img_tag and title_tag:
                        ongoing.append({
                            "title": title_tag.get_text(strip=True),
                            "slug": link_tag['href'].strip('/').split('/')[-1],
                            "image": img_tag['src'],
                            "episode": ep,
                            "day": day,
                            "date": date,
                            "url": link_tag['href']
                        })

        return {"ongoing": ongoing, "complete": []}

    def get_ongoing_anime(self, page=1):
        url = f"{self.BASE_URL}/ongoing-anime/page/{page}/" if page > 1 else f"{self.BASE_URL}/ongoing-anime/"
        soup = self._get_soup(url)
        if not soup:
            return []

        anime_list = []
        venz = soup.find('div', class_='venz')
        if venz:
            for item in venz.find_all('li'):
                thumb = item.find('div', class_='thumb')
                if thumb:
                    link_tag = thumb.find('a')
                    img_tag = thumb.find('img')
                    title_tag = thumb.find('h2', class_='jdlflm')

                    detpost = item.find('div', class_='detpost')
                    ep = detpost.find('div', class_='epz').get_text(strip=True) if detpost and detpost.find('div', class_='epz') else ""

                    if link_tag and img_tag and title_tag:
                         anime_list.append({
                            "title": title_tag.get_text(strip=True),
                            "slug": link_tag['href'].strip('/').split('/')[-1],
                            "image": img_tag['src'],
                            "episode": ep,
                            "url": link_tag['href']
                        })
        return anime_list

    def get_anime_list(self):
        url = f"{self.BASE_URL}/anime-list/"
        soup = self._get_soup(url)
        if not soup:
            return []

        anime_list = []
        content = soup.find('div', id='abtext')
        if content:
             for item in content.find_all('div', class_='jdlbar'):
                 for link in item.find_all('a'):
                     anime_list.append({
                         "title": link.get_text(strip=True),
                         "slug": link['href'].strip('/').split('/')[-1],
                         "url": link['href']
                     })
        return anime_list

    def get_genre_list(self):
        url = f"{self.BASE_URL}/genre-list/"
        soup = self._get_soup(url)
        if not soup:
            return []

        genres = []
        genre_list = soup.find('ul', class_='genres')
        if genre_list:
            for link in genre_list.find_all('a'):
                genres.append({
                    "name": link.get_text(strip=True),
                    "slug": link['href'].strip('/').split('/')[-1],
                    "url": link['href']
                })
        return genres

    def search_anime(self, query):
        url = f"{self.BASE_URL}/?s={query}&post_type=anime"
        soup = self._get_soup(url)
        if not soup:
            return []

        results = []
        ul = soup.find('ul', class_='chivsrc')
        if ul:
            for item in ul.find_all('li'):
                img_tag = item.find('img')
                link_tag = item.find('h2').find('a') if item.find('h2') else item.find('a')

                if link_tag:
                    results.append({
                        "title": link_tag.get_text(strip=True),
                        "slug": link_tag['href'].strip('/').split('/')[-1],
                        "image": img_tag['src'] if img_tag else "",
                        "url": link_tag['href'],
                        "genres": [g.get_text(strip=True) for g in item.find_all('a', rel='tag')]
                    })
        return results

    def get_anime_details(self, slug):
        url = f"{self.BASE_URL}/anime/{slug}/"
        soup = self._get_soup(url)
        if not soup:
            return None

        details = {}
        # Title
        info_div = soup.find('div', class_='fotoanime')
        if info_div:
            img = info_div.find('img')
            details['image'] = img['src'] if img else ""

        info_z = soup.find('div', class_='infozingle')
        if info_z:
            p_tags = info_z.find_all('p')
            for p in p_tags:
                text = p.get_text(strip=True)
                if ":" in text:
                    key, val = text.split(':', 1)
                    details[key.lower().replace(' ', '_')] = val.strip()

        # Synopsis
        synops = soup.find('div', class_='sinopc')
        details['synopsis'] = synops.get_text(strip=True) if synops else ""

        # Title usually in h1 inside div.jdlrx
        jdlrx = soup.find('div', class_='jdlrx')
        if jdlrx and jdlrx.find('h1'):
            details['title'] = jdlrx.find('h1').get_text(strip=True)
        else:
            details['title'] = slug

        # Episode List
        episode_list = []
        for episodelist_div in soup.find_all('div', class_='episodelist'):
             for item in episodelist_div.find_all('li'):
                link = item.find('a')
                date = item.find('span', class_='zeebr').get_text(strip=True) if item.find('span', class_='zeebr') else ""
                if link:
                    slug_ep = link['href'].strip('/').split('/')[-1]
                    if not any(e['slug'] == slug_ep for e in episode_list):
                        episode_list.append({
                            "title": link.get_text(strip=True),
                            "slug": slug_ep,
                            "url": link['href'],
                            "date": date
                        })
        details['episodes'] = episode_list
        return details

    def get_episode_details(self, slug):
        url = f"{self.BASE_URL}/episode/{slug}/"
        soup = self._get_soup(url)
        if not soup:
            return None

        data = {}

        # Title
        h1 = soup.find('h1', class_='posttl')
        data['title'] = h1.get_text(strip=True) if h1 else slug

        # Navigation (Next/Prev)
        prevnext = soup.find('div', class_='prevnext')
        if prevnext:
            flir = prevnext.find('div', class_='flir')
            if flir:
                links = flir.find_all('a')
                for link in links:
                    if "Next" in link.get_text():
                        data['next_episode'] = link['href'].strip('/').split('/')[-1]
                    elif "Prev" in link.get_text():
                        data['prev_episode'] = link['href'].strip('/').split('/')[-1]

        # Stream Mirrors
        mirrors = {}
        mirror_stream = soup.find('div', class_='mirrorstream')
        if mirror_stream:
            for qual_ul in mirror_stream.find_all('ul'):
                quality = qual_ul.get('class')[0] if qual_ul.get('class') else "unknown" # e.g., m360p
                if quality.startswith('m'): quality = quality[1:]

                q_mirrors = []
                for li in qual_ul.find_all('li'):
                    a = li.find('a')
                    if a:
                        content = a.get('data-content')
                        host = a.get_text(strip=True)
                        q_mirrors.append({
                            "host": host,
                            "data_content": content
                        })
                mirrors[quality] = q_mirrors

        data['mirrors'] = mirrors

        # Default Iframe
        iframe = soup.find('iframe')
        data['default_stream'] = iframe['src'] if iframe else ""

        return data

    def resolve_stream(self, data_content):
        # Step 1: Get Nonce
        try:
            res = self.session.post(
                f"{self.BASE_URL}/wp-admin/admin-ajax.php",
                data={"action": "aa1208d27f29ca340c92c66d1926f13f"},
                timeout=10
            )
            res.raise_for_status()
            response_json = res.json()
            nonce = response_json.get('data')
        except Exception as e:
            print(f"Error getting nonce: {e}")
            return None

        if not nonce:
            return None

        # Step 2: Get Embed Code
        try:
            params = json.loads(base64.b64decode(data_content).decode('utf-8'))

            payload = params.copy()
            payload['nonce'] = nonce
            payload['action'] = "2a3505c93b0035d3f455df82bf976b84"

            res = self.session.post(
                f"{self.BASE_URL}/wp-admin/admin-ajax.php",
                data=payload,
                timeout=10
            )
            res.raise_for_status()
            embed_data = res.json().get('data')
            if embed_data:
                html_embed = base64.b64decode(embed_data).decode('utf-8')
                soup = BeautifulSoup(html_embed, 'lxml')
                iframe = soup.find('iframe')
                if iframe:
                    return iframe['src']
        except Exception as e:
            print(f"Error resolving stream: {e}")
            return None

        return None

    def extract_video_from_desustream(self, url):
        try:
            soup = self._get_soup(url)
            if not soup: return None

            iframe = soup.find('iframe')
            if iframe:
                next_url = iframe['src']
                if "blogger.com" in next_url:
                    return self.extract_video_from_blogger(next_url)
            return None
        except Exception as e:
            print(f"Error extracting from desustream: {e}")
            return None

    def extract_video_from_blogger(self, url):
        try:
            soup = self._get_soup(url)
            if not soup:
                print("Soup not found for blogger url")
                return None

            scripts = soup.find_all('script')
            for script in scripts:
                content = script.string or script.get_text()
                if content and 'VIDEO_CONFIG' in content:
                    # Improved regex to handle various formats
                    json_str = re.search(r'VIDEO_CONFIG\s*=\s*(\{.*?\})\s*(?:;|</script>)', content, re.DOTALL)
                    if not json_str:
                         json_str = re.search(r'VIDEO_CONFIG\s*=\s*(\{.*?\})\s*$', content, re.DOTALL)

                    if json_str:
                        try:
                            config = json.loads(json_str.group(1))
                            if 'streams' in config and config['streams']:
                                return config['streams'][0]['play_url']
                        except json.JSONDecodeError:
                            print("Error decoding VIDEO_CONFIG JSON")
            print("VIDEO_CONFIG not found in blogger page")
            return None
        except Exception as e:
            print(f"Error extracting from blogger: {e}")
            return None
