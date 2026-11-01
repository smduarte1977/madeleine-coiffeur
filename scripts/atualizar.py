"""Atualiza os dados do painel da Madeleine Coiffeur a partir do Windsor.ai.

Roda no GitHub Actions (veja .github/workflows/atualizar.yml). Precisa do segredo
WINDSOR_API_KEY. Grava data/site.json, as miniaturas em assets/thumbs/ e assets/thumbs.js.
Se uma consulta falhar, mantém os dados anteriores dela.
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IG = '17841401334230577'          # Instagram @madeleinecoiffeur
ADS = '2109889396167857'          # Conta de anúncios CA Madeleine Coiffeur
FB_PAGE = '2076420892601383'      # Página do Facebook (foto de perfil)
KEY = os.environ.get('WINDSOR_API_KEY', '').strip()

QUERIES = {
    'profile': ('instagram', IG, {'date_preset': 'last_1dT'}, ['username', 'name', 'biography', 'website', 'followers_count', 'follows_count', 'media_count']),
    'followers_daily': ('instagram', IG, {'date_preset': 'last_30d'}, ['date', 'follower_count_1d', 'reach']),
    'daily': ('instagram', IG, {'date_preset': 'last_720d'}, ['date', 'views', 'total_interactions', 'likes', 'saves', 'shares', 'comments', 'follows_and_unfollows']),
    'media': ('instagram', IG, {'date_preset': 'last_2years'}, ['timestamp', 'media_id', 'media_type', 'media_permalink', 'media_caption', 'media_reach', 'media_engagement', 'media_like_count', 'media_saved', 'media_shares', 'media_comments_count', 'media_views', 'media_follows', 'media_thumbnail_url', 'media_url']),
    'gender': ('instagram', IG, {'date_preset': 'last_1dT'}, ['audience_gender_name', 'audience_gender_size']),
    'age': ('instagram', IG, {'date_preset': 'last_1dT'}, ['audience_age_name', 'audience_age_size']),
    'cities': ('instagram', IG, {'date_preset': 'last_1dT'}, ['city', 'audience_city_size']),
    'ads_media': ('facebook', ADS, {'date_preset': 'last_2years'}, ['campaign', 'adset_name', 'ad_name', 'effective_instagram_media_id', 'source_instagram_media_id', 'spend']),
}


def get(url, timeout=180):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def windsor(connector, account, extra, fields):
    q = {'api_key': KEY, 'fields': ','.join(fields), 'select_accounts': account, **extra}
    body = json.loads(get('https://connectors.windsor.ai/' + connector + '?' + urllib.parse.urlencode(q)))
    rows = body.get('data', body) if isinstance(body, dict) else body
    if not isinstance(rows, list):
        raise ValueError('resposta inesperada: ' + str(body)[:200])
    return rows


def save_thumb(url, path):
    im = Image.open(io.BytesIO(get(url, 60))).convert('RGB')
    w, h = im.size
    s = max(200 / w, 250 / h)
    im = im.resize((round(w * s), round(h * s)))
    l, t = (im.width - 200) // 2, (im.height - 250) // 2
    im.crop((l, t, l + 200, t + 250)).save(path, 'JPEG', quality=70)


def main():
    if not KEY:
        sys.exit('Falta o segredo WINDSOR_API_KEY no GitHub.')
    site_path = os.path.join(ROOT, 'data', 'site.json')
    site = json.load(open(site_path, encoding='utf-8')) if os.path.exists(site_path) else {}
    ok = 0
    for name, (connector, account, extra, fields) in QUERIES.items():
        try:
            site[name] = windsor(connector, account, extra, fields)
            ok += 1
            print(f'{name}: {len(site[name])} linhas')
        except Exception as e:  # keep the previous rows for this source
            print(f'{name}: falhou ({e}); mantendo os dados anteriores')
    if ok == 0:
        sys.exit('Nenhuma consulta funcionou. Confira a chave do Windsor.')

    # Thumbnails: download only posts that don't have one yet.
    thumbs_dir = os.path.join(ROOT, 'assets', 'thumbs')
    os.makedirs(thumbs_dir, exist_ok=True)
    for m in site.get('media', []):
        path = os.path.join(thumbs_dir, str(m['media_id']) + '.jpg')
        url = m.pop('media_thumbnail_url', None) or m.pop('media_url', None)
        m.pop('media_url', None)
        if url and not os.path.exists(path):
            try:
                save_thumb(url, path)
            except Exception as e:
                print('miniatura falhou', m['media_id'], e)
    have = {f[:-4] for f in os.listdir(thumbs_dir) if f.endswith('.jpg')}
    thumbs = {i: 'assets/thumbs/' + i + '.jpg' for i in sorted(have)}
    open(os.path.join(ROOT, 'assets', 'thumbs.js'), 'w', encoding='utf-8').write('window.DVM_THUMBS=' + json.dumps(thumbs) + ';\n')

    try:
        im = Image.open(io.BytesIO(get(f'https://graph.facebook.com/{FB_PAGE}/picture?type=large', 60))).convert('RGB')
        s = min(im.size)
        im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((240, 240)).save(os.path.join(ROOT, 'assets', 'avatar.jpg'), 'JPEG', quality=85)
    except Exception as e:
        print('foto de perfil falhou', e)

    if site.get('profile'):
        site['profile'][0]['data_fetched_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    json.dump(site, open(site_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print('pronto')


if __name__ == '__main__':
    main()
