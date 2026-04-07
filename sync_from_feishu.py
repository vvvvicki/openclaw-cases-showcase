import json, sys, os, urllib.request

FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.environ.get('FEISHU_APP_SECRET', '')
FEISHU_APP_TOKEN = os.environ.get('FEISHU_APP_TOKEN', 'RDaKbFv7EaWDnWsjU6fcocYvnNh')
FEISHU_TABLE_ID = os.environ.get('FEISHU_TABLE_ID', 'tblygXXyTmKGUp6q')

print('APP_ID=' + FEISHU_APP_ID[:8] + '...', file=sys.stderr)
print('APP_SECRET=' + FEISHU_APP_SECRET[:4] + '...', file=sys.stderr)

req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=json.dumps({'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    token_data = json.loads(resp.read())
token = token_data.get('tenant_access_token', '')
code = token_data.get('code')
if not token or code != 0:
    print('TOKEN_ERROR code=' + str(code) + ' msg=' + str(token_data.get('msg','')), file=sys.stderr)
    sys.exit(1)
print('TOKEN_OK len=' + str(len(token)), file=sys.stderr)

all_records = []
page_token = ''
while True:
    url = 'https://open.feishu.cn/open-apis/bitable/v1/apps/' + FEISHU_APP_TOKEN + '/tables/' + FEISHU_TABLE_ID + '/records?page_size=500'
    if page_token:
        url = url + '&page_token=' + page_token
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    items = data.get('data', {}).get('items', [])
    all_records.extend(items)
    if not data.get('data', {}).get('has_more'):
        break
    pt = data.get('data', {}).get('page_token', '')
    if not pt:
        break
    page_token = pt

print('Fetched ' + str(len(all_records)) + ' records', file=sys.stderr)
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
si = html.find('const allItems = [')
ei = html.find('];\nfunction diffClass')
if si == -1 or ei == -1:
    print('ERROR: markers not found', file=sys.stderr)
    sys.exit(1)

def score(r):
    fd = r.get('fields', {})
    s = fd.get('评估分')
    if s is None: return 0
    try: return float(s)
    except: return 0

filtered = [r for r in all_records if score(r) >= 7]
filtered.sort(key=lambda r: (-score(r), -float(r.get('fields',{}).get('热度信号') or 0)))

seen = {}
for r in filtered:
    link = r.get('fields',{}).get('案例链接',{}) or {}
    u = (link.get('link','') if isinstance(link,dict) else '') or ''
    if u and (u not in seen or score(r) > score(seen[u])):
        seen[u] = r

final = list(seen.values())[:50]
final.sort(key=lambda r: (-score(r), -float(r.get('fields',{}).get('热度信号') or 0)))

def esc(v):
    s = str(v) or ''
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', ' ')
    s = s.replace('\r', '')
    return s

data = []
for r in final:
    fld = r.get('fields',{})
    link = fld.get('案例链接',{}) or {}
    u = (link.get('link','') if isinstance(link,dict) else '') or ''
    title = fld.get('案例名称') or '无标题'
    plat = fld.get('来源平台') or '其他'
    s = score(r)
    diff = fld.get('迁移难度') or '中等'
    desc = fld.get('核心玩法描述') or ''
    tags = []
    for k in ['迁移难度','来源平台']:
        v = fld.get(k)
        if v: tags.append(v)
    h = fld.get('启发价值') or ''
    for kw in ['多Agent','变现','Telegram','自动化','本地部署','入门']:
        if kw in h: tags.append(kw)
    tags = tags[:3]
    data.append('{"id":"'+esc(r['id'])+'","title":"'+esc(title)+'","platform":"'+esc(plat)+'","score":'+str(s)+',"difficulty":"'+esc(diff)+'","description":"'+esc(desc)+'","url":"'+esc(u)+'","tags":'+json.dumps(tags,ensure_ascii=False)+'}')

new_data = 'const allItems = [\n      ' + ',\n      '.join(data) + '\n    ];'
new_html = html[:si] + new_data + html[ei:]
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print('Written: ' + str(len(final)) + ' records', file=sys.stderr)
print('SUCCESS')
