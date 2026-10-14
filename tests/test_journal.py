import io,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
from PIL import Image
sandbox=tempfile.TemporaryDirectory();os.environ['JOURNAL_DATA']=sandbox.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'campsite_journal'))
from app import app,connection,DEFAULTS,FIELDS
from mobile_access import channel_app
class JournalTest(unittest.TestCase):
 def setUp(self):
  self.client=app.test_client();self.headers={'X-Camp-Request':'1'}
  with connection() as c:
   c.execute('DELETE FROM records');c.execute('DELETE FROM devices');c.execute('UPDATE settings SET body=? WHERE id=1',(json.dumps(DEFAULTS),))
 def record(self,**extra):
  data={'name':'테스트 캠핑장','location':'강원도','price':120000,'checkin':'2026-10-01','checkout':'2026-10-03',**extra}
  r=self.client.post('/api/records',json=data,headers=self.headers);self.assertEqual(r.status_code,201);return r.json['id']
 def test_persistence_and_date_validation(self):
  ident=self.record();r=self.client.get('/api/state').json['records'][0];self.assertEqual(r['id'],ident);self.assertEqual(r['price'],120000)
  self.assertEqual(self.client.put('/api/records/'+ident,json={'name':'변경','checkin':'2026-10-03','checkout':'2026-10-01'},headers=self.headers).status_code,400)
  self.assertEqual(self.client.post('/api/records',json={'name':'X','booking_url':'javascript:alert(1)'},headers=self.headers).status_code,400)
 def test_photo_and_layout_upload_delete(self):
  ident=self.record()
  for kind in ['gallery','layout']:
   image=io.BytesIO();Image.new('RGB',(20,20),'green').save(image,'PNG');image.seek(0)
   r=self.client.post('/api/records/'+ident+'/photos/'+kind,data={'photos':(image,'picture.png')},headers=self.headers)
   self.assertEqual(r.status_code,200)
  r=self.client.get('/api/state').json['records'][0];self.assertEqual(len(r['photos']),2)
  photo=r['photos'][0]['id'];response=self.client.get('/photos/'+photo);self.assertEqual(response.status_code,200);response.close()
  self.assertEqual(self.client.delete('/api/photos/'+photo,headers=self.headers).status_code,200);self.assertEqual(self.client.get('/photos/'+photo).status_code,404)
  self.client.delete('/api/records/'+ident,headers=self.headers)
  self.assertEqual(self.client.get('/api/state').json['records'],[])
 def test_atomic_bad_upload(self):
  ident=self.record();r=self.client.post('/api/records/'+ident+'/photos/gallery',data={'photos':(io.BytesIO(b'not image'),'bad.jpg')},headers=self.headers);self.assertEqual(r.status_code,400)
  self.assertEqual(self.client.get('/api/state').json['records'][0]['photos'],[])
 def test_display_settings_minimums_order_visibility(self):
  s=json.loads(json.dumps(DEFAULTS));s['order']=list(reversed(FIELDS));s['visible']['price']=False;s['desktop']['font']=8;s['desktop']['padding']=2;s['desktop']['widths']['name']=20
  self.assertEqual(self.client.put('/api/settings',json=s,headers=self.headers).status_code,200)
  actual=self.client.get('/api/state').json['settings'];self.assertEqual(actual['order'],s['order']);self.assertFalse(actual['visible']['price']);self.assertEqual(actual['display_mobile']['font'],12)
  s['desktop']['widths']['name']=19;self.assertEqual(self.client.put('/api/settings',json=s,headers=self.headers).status_code,400)
 def test_csrf_and_external_auth_and_revocation(self):
  self.assertEqual(self.client.post('/api/records',json={'name':'bad'}).status_code,403)
  ext=app.test_client();outside={'journal.entrypoint':'external','SERVER_PORT':'8098'}
  self.assertEqual(ext.get('/api/state',environ_overrides=outside).status_code,401)
  self.assertEqual(ext.get('/api/state',headers={'X-Ingress-Path':'fake'},environ_overrides=outside).status_code,401)
  self.client.put('/api/mobile/config',json={'enabled':True,'external_url':'https://ha.badara.co.kr/campsite-journal/'},headers=self.headers)
  pair=self.client.post('/api/mobile/devices',json={'name':'test'},headers=self.headers).json
  self.assertEqual(ext.post('/api/mobile/session',json={'key':pair['token']},environ_overrides=outside).status_code,200)
  auth={'Authorization':'Bearer '+pair['token'],'X-Camp-Request':'1'}
  self.assertEqual(ext.get('/api/state',headers=auth,environ_overrides=outside).status_code,200)
  self.assertEqual(ext.post('/api/mobile/devices',json={'name':'evil'},headers=auth,environ_overrides=outside).status_code,403)
  self.client.post('/api/mobile/devices/'+pair['id']+'/revoke',json={},headers=self.headers)
  self.assertEqual(ext.get('/api/state',headers=auth,environ_overrides=outside).status_code,401)
 def test_backup_excludes_pairing_keys(self):
  self.record();r=self.client.get('/api/backup');self.assertEqual(r.status_code,200)
  with zipfile.ZipFile(io.BytesIO(r.data)) as z:
   data=json.loads(z.read('journal.json'));self.assertEqual(len(data['records']),1);self.assertNotIn('mobile',data['settings']);self.assertNotIn('devices',data)
if __name__=='__main__':unittest.main()
