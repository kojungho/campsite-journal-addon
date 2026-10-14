"""Persistent campsite journal, HA Ingress and isolated paired-device listener."""
import io,json,os,sqlite3,uuid,zipfile
from pathlib import Path
from datetime import date
from contextlib import contextmanager
from flask import Flask,request,jsonify,abort,send_file
from PIL import Image,UnidentifiedImageError,ImageOps
from pillow_heif import register_heif_opener
register_heif_opener()
from mobile_access import install_mobile,channel_app
from address_search import search as search_address

DATA=Path(os.getenv('JOURNAL_DATA','./.local-data'));DATA.mkdir(parents=True,exist_ok=True)
MEDIA=DATA/'photos';MEDIA.mkdir(exist_ok=True)
FIELDS=['platform','booking_url','name','location','map_url','site','price','checkin','checkout','photos','layout','notes']
LABELS=['예약 플랫폼','예약 링크','캠핑장명','위치','지도 링크','사이트명','가격','입실','퇴실','사진','배치도','메모']
DEFAULTS={'order':FIELDS,'visible':{k:k!='notes' for k in FIELDS},'desktop':{'widths':{k:140 for k in FIELDS},'font':14,'padding':10},'mobile':{'widths':{k:100 for k in FIELDS},'font':12,'padding':6},'external':{},'picker':'files'}
# Device config uses mobile key; display settings use display_mobile to keep schemas separate.
DEFAULTS['display_mobile']=DEFAULTS.pop('mobile')
app=Flask(__name__);app.config['MAX_CONTENT_LENGTH']=64*1024*1024
@contextmanager
def connection():
 c=sqlite3.connect(DATA/'journal.sqlite3',timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:yield c;c.commit()
 except: c.rollback();raise
 finally:c.close()
with connection() as c:
 c.executescript('CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,body TEXT NOT NULL);CREATE TABLE IF NOT EXISTS photos(id TEXT PRIMARY KEY,record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,kind TEXT NOT NULL,name TEXT NOT NULL);CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY,body TEXT NOT NULL);')
 c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(DEFAULTS),))
def get_settings(c):return json.loads(c.execute('SELECT body FROM settings WHERE id=1').fetchone()[0])
mobile=install_mobile(app,connection,get_settings,DATA)
@app.before_request
def guard():
 result=mobile['guard']()
 if result is not None:return result
 if request.method in ('POST','PUT','DELETE') and request.path!='/api/mobile/session' and request.headers.get('X-Camp-Request')!='1':abort(403)
@app.after_request
def headers(r):
 r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='strict-origin-when-cross-origin';r.headers['Cache-Control']='no-store' if request.path.startswith('/api/') else 'no-cache'
 r.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-src https://www.openstreetmap.org; base-uri 'self'; form-action 'self'"
 return r
@app.errorhandler(ValueError)
def invalid(e):return jsonify(error=str(e)),400
@app.errorhandler(413)
def too_large(e):return jsonify(error='한 번에 64MB 이하로 첨부해주세요.'),413
@app.get('/')
def index():return app.send_static_file('index.html')
@app.get('/api/state')
def state():
 with connection() as c:
  rows=[{**json.loads(r['body']),'id':r['id'],'photos':[dict(p) for p in c.execute('SELECT * FROM photos WHERE record_id=?',(r['id'],))]} for r in c.execute('SELECT * FROM records ORDER BY rowid DESC')]
  return jsonify(records=rows,settings=get_settings(c),admin=mobile['admin'](),version=os.getenv('JOURNAL_VERSION','1.0.0'))
def clean(raw):
 if not isinstance(raw,dict):raise ValueError('기록 형식이 올바르지 않습니다.')
 b={k:raw.get(k,'') for k in FIELDS if k not in ('photos','layout')}
 for k,v in b.items():
  if not isinstance(v,(str,int,float)) or len(str(v))>10000:raise ValueError('입력값이 너무 길거나 올바르지 않습니다.')
  if k!='price':b[k]=str(v).strip()
 if not b['name']:raise ValueError('캠핑장명을 입력해주세요.')
 for k in ('booking_url','map_url'):
  if b[k] and not b[k].startswith(('https://','http://')):raise ValueError('링크는 https:// 또는 http://로 시작해야 합니다.')
 try:b['price']=int(b['price'] or 0)
 except (ValueError,TypeError):raise ValueError('가격은 원 단위 정수로 입력해주세요.')
 if b['price']<0:raise ValueError('가격은 0원 이상이어야 합니다.')
 for k in ('checkin','checkout'):
  if b[k]:
   try:date.fromisoformat(b[k])
   except ValueError:raise ValueError('숙박 날짜를 확인해주세요.')
 if b['checkout'] and not b['checkin']:raise ValueError('입실일을 먼저 입력해주세요.')
 if b['checkin'] and b['checkout'] and b['checkout']<b['checkin']:raise ValueError('퇴실일은 입실일 이후여야 합니다.')
 for k in ('lat','lng'):
  v=raw.get(k)
  if v in ('',None):b[k]=None
  else:
   try:v=float(v)
   except (ValueError,TypeError):raise ValueError('좌표는 숫자로 입력해주세요.')
   if not -(90 if k=='lat' else 180)<=v<=(90 if k=='lat' else 180):raise ValueError('좌표 범위를 확인해주세요.')
   b[k]=v
 if (b['lat'] is None)!=(b['lng'] is None):raise ValueError('위도와 경도를 함께 입력해주세요.')
 return b
@app.get('/api/addresses')
def addresses():
 body,status=search_address(request.args.get('q',''))
 return jsonify(body),status

@app.post('/api/records')
def create():
 b=clean(request.get_json());ident=str(uuid.uuid4())
 with connection() as c:c.execute('INSERT INTO records VALUES(?,?)',(ident,json.dumps(b,ensure_ascii=False)))
 return jsonify(id=ident),201
@app.put('/api/records/<ident>')
def update(ident):
 b=clean(request.get_json())
 with connection() as c:
  if not c.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(b,ensure_ascii=False),ident)).rowcount:abort(404)
 return jsonify(ok=True)
@app.delete('/api/records/<ident>')
def delete(ident):
 with connection() as c:
  names=[p[0] for p in c.execute('SELECT id FROM photos WHERE record_id=?',(ident,))]
  if not c.execute('DELETE FROM records WHERE id=?',(ident,)).rowcount:abort(404)
 for name in names:(MEDIA/(name+'.jpg')).unlink(missing_ok=True)
 return jsonify(ok=True)
@app.post('/api/records/<ident>/photos/<kind>')
def upload(ident,kind):
 if kind not in ('gallery','layout'):abort(400)
 staged=[]
 try:
  files=request.files.getlist('photos')
  if not files:raise ValueError('사진을 선택해주세요.')
  for f in files:
   ident_photo=str(uuid.uuid4())
   try:
    with Image.open(f.stream) as im:
     if im.format not in ('JPEG','PNG','WEBP','GIF','HEIF','HEIC'):raise ValueError('JPG, PNG, WebP, GIF 사진을 선택해주세요.')
     im.load();im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((3200,3200));buf=io.BytesIO();im.save(buf,'JPEG',quality=90)
   except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ValueError('사진을 읽을 수 없습니다. HEIC 사진은 JPG로 변환해주세요.')
   staged.append((ident_photo,Path(f.filename or '사진').name,buf.getvalue()))
  with connection() as c:
   if not c.execute('SELECT 1 FROM records WHERE id=?',(ident,)).fetchone():abort(404)
   for pid,name,content in staged:
    (MEDIA/(pid+'.jpg')).write_bytes(content);c.execute('INSERT INTO photos VALUES(?,?,?,?)',(pid,ident,kind,name))
 except Exception:
  for pid,_,_ in staged:(MEDIA/(pid+'.jpg')).unlink(missing_ok=True)
  raise
 return jsonify(ok=True,count=len(staged))
@app.get('/photos/<pid>')
def photo(pid):
 with connection() as c:
  if not c.execute('SELECT 1 FROM photos WHERE id=?',(pid,)).fetchone():abort(404)
 return send_file(MEDIA/(pid+'.jpg'),mimetype='image/jpeg')
@app.delete('/api/photos/<pid>')
def remove_photo(pid):
 with connection() as c:
  if not c.execute('DELETE FROM photos WHERE id=?',(pid,)).rowcount:abort(404)
 (MEDIA/(pid+'.jpg')).unlink(missing_ok=True)
 return jsonify(ok=True)
@app.put('/api/settings')
def settings():
 raw=request.get_json()
 if not isinstance(raw,dict):raise ValueError('설정 형식이 올바르지 않습니다.')
 order=raw.get('order',[])
 if len(order)!=len(FIELDS) or set(order)!=set(FIELDS):raise ValueError('항목 순서를 확인해주세요.')
 visible=raw.get('visible',{})
 if set(visible)!=set(FIELDS) or any(type(v)!=bool for v in visible.values()) or not any(visible.values()):raise ValueError('최소 한 항목을 표시해주세요.')
 display={}
 for key in ('desktop','display_mobile'):
  x=raw.get(key,{})
  try:
   font=int(x['font']);padding=int(x['padding']);widths={k:int(x['widths'][k]) for k in FIELDS}
  except (KeyError,ValueError,TypeError):raise ValueError('화면 설정을 확인해주세요.')
  if not 8<=font<=60 or not 2<=padding<=60 or any(not 20<=v<=1200 for v in widths.values()):raise ValueError('열 너비 20px, 글자 8px, 여백 2px 이상으로 설정해주세요.')
  display[key]={'font':font,'padding':padding,'widths':widths}
 if raw.get('picker') not in ('files','gallery'):raise ValueError('사진 선택 방식을 확인해주세요.')
 with connection() as c:
  s=get_settings(c);s.update(order=order,visible=visible,picker=raw['picker'],**display);c.execute('UPDATE settings SET body=? WHERE id=1',(json.dumps(s,ensure_ascii=False),))
 return jsonify(ok=True)
@app.get('/api/backup')
def backup():
 out=io.BytesIO()
 with connection() as c,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  # Serialize only journal data; paired device secrets are excluded.
  records=[dict(r) for r in c.execute('SELECT * FROM records')];photos=[dict(r) for r in c.execute('SELECT * FROM photos')]
  s=get_settings(c);s.pop('mobile',None)
  z.writestr('journal.json',json.dumps({'records':records,'photos':photos,'settings':s},ensure_ascii=False))
  for p in photos:z.write(MEDIA/(p['id']+'.jpg'),'photos/'+p['id']+'.jpg')
 out.seek(0);return send_file(out,as_attachment=True,download_name='캠핑장기록-백업.zip')
if __name__=='__main__':
 from waitress import serve
 import threading
 threading.Thread(target=lambda:serve(channel_app(app,'external'),host='0.0.0.0',port=8098),daemon=True).start()
 serve(channel_app(app,'ingress'),host=os.getenv('JOURNAL_HOST','0.0.0.0'),port=int(os.getenv('JOURNAL_PORT','8099')))
