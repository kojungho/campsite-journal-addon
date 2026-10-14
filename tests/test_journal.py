import io,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
from PIL import Image
sandbox=tempfile.TemporaryDirectory();os.environ['JOURNAL_DATA']=sandbox.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'campsite_journal'))
from app import app,connection,DEFAULTS,FIELDS,MEDIA
from unittest.mock import patch
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
 def test_photo_memo_and_scroll_position(self):
  ident=self.record();image=io.BytesIO();Image.new('RGB',(10,10),'blue').save(image,'PNG');image.seek(0)
  self.client.post('/api/records/'+ident+'/photos/gallery',data={'photos':(image,'memo.png')},headers=self.headers)
  photo=self.client.get('/api/state').json['records'][0]['photos'][0];self.assertEqual(photo['memo'],'')
  self.assertEqual(self.client.put('/api/photos/'+photo['id'],json={'memo':'첫날의 캠핑\n노을'},headers=self.headers).status_code,200)
  self.assertEqual(self.client.get('/api/state').json['records'][0]['photos'][0]['memo'],'첫날의 캠핑\n노을')
  self.assertEqual(self.client.put('/api/photos/'+photo['id'],json={'memo':'x'*2001},headers=self.headers).status_code,400)
  self.assertEqual(self.client.put('/api/photos/'+photo['id'],json={'memo':'bad'}).status_code,403)
  self.assertEqual(self.client.put('/api/photos/missing',json={'memo':'x'},headers=self.headers).status_code,404)
  settings=self.client.get('/api/state').json['settings']
  for side in ('left','right'):
   for pos in ('top','middle','bottom'):
    settings['scroll_top']=side+'-'+pos;self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,200);self.assertEqual(self.client.get('/api/state').json['settings']['scroll_top'],side+'-'+pos)
  settings['scroll_top']='invalid';self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,400)
 def test_address_position_update_preserves_other_fields(self):
  ident=self.record(notes='유지할 메모',booking_url='https://example.com')
  self.assertEqual(self.client.put('/api/records/'+ident+'/position',json={'address':'다른 주소','lat':37,'lng':128},headers=self.headers).status_code,409)
  self.assertEqual(self.client.put('/api/records/'+ident+'/position',json={'address':'강원도','lat':37,'lng':128},headers=self.headers).status_code,200)
  self.client.put('/api/records/'+ident+'/position',json={'address':'강원도','lat':38,'lng':129},headers=self.headers)
  record=self.client.get('/api/state').json['records'][0];self.assertEqual(record['lat'],37);self.assertEqual(record['notes'],'유지할 메모');self.assertEqual(record['booking_url'],'https://example.com')
 def test_detail_order_and_icon_size_settings(self):
  settings=self.client.get('/api/state').json['settings'];original=settings['detail_order'][:]
  self.assertEqual(settings['desktop']['link_size'],20)
  settings['detail_order']=list(reversed(original));settings['desktop']['link_size']=32;settings['display_mobile']['link_size']=16
  self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,200)
  saved=self.client.get('/api/state').json['settings'];self.assertEqual(saved['detail_order'],list(reversed(original)));self.assertEqual(saved['desktop']['link_size'],32);self.assertEqual(saved['display_mobile']['link_size'],16)
  settings['desktop']['link_size']=81;self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,400)
  settings['desktop']['link_size']=32;settings['detail_order'][0]=['invalid'];self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,400)
  settings['detail_order']=original[:-1];self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,400)
  saved.pop('detail_order');self.assertEqual(self.client.put('/api/settings',json=saved,headers=self.headers).status_code,200);self.assertEqual(self.client.get('/api/state').json['settings']['detail_order'],list(reversed(original)))
 def test_old_list_columns_upgrade_and_derived_nights(self):
  old=json.loads(json.dumps(DEFAULTS));old['order'].remove('nights');old['visible'].pop('nights');old['visible']['price']=False
  for mode in ('desktop','display_mobile'):old[mode]['widths'].pop('nights');old[mode]['widths']['checkout']=123
  with connection() as c:c.execute('UPDATE settings SET body=? WHERE id=1',(json.dumps(old),))
  upgraded=self.client.get('/api/state').json['settings'];self.assertEqual(upgraded['order'].index('nights'),upgraded['order'].index('checkout')+1);self.assertEqual(upgraded['desktop']['widths']['nights'],123);self.assertFalse(upgraded['visible']['price'])
  self.assertEqual(self.client.put('/api/settings',json=old,headers=self.headers).status_code,200)
  ident=self.record(nights='999');record=self.client.get('/api/state').json['records'][0];self.assertEqual(record['id'],ident);self.assertNotIn('nights',record);self.assertEqual(record['checkout'],'2026-10-03')
 def test_clone_copies_metadata_photos_and_memos_independently(self):
  source=self.record(platform='캠핏',notes='원본 메모',lat=37,lng=128)
  for kind in ('gallery','layout'):
   image=io.BytesIO();Image.new('RGB',(10,10),'green').save(image,'PNG');image.seek(0)
   self.client.post('/api/records/'+source+'/photos/'+kind,data={'photos':(image,kind+'.png')},headers=self.headers)
  original=self.client.get('/api/state').json['records'][0]
  for p in original['photos']:self.client.put('/api/photos/'+p['id'],json={'memo':'사진 메모 '+p['kind']},headers=self.headers)
  original=self.client.get('/api/state').json['records'][0];payload={k:v for k,v in original.items() if k not in ('id','photos')};payload.update(clone_from=source,name='다음 방문',checkin='2026-11-01',checkout='2026-11-04')
  response=self.client.post('/api/records',json=payload,headers=self.headers);self.assertEqual(response.status_code,201);newid=response.json['id'];records=self.client.get('/api/state').json['records'];clone=next(r for r in records if r['id']==newid)
  self.assertEqual(next(r for r in records if r['id']==source),original);self.assertEqual(clone['name'],'다음 방문');self.assertEqual(clone['lat'],37);self.assertEqual(clone['platform'],'캠핏');self.assertEqual(clone['checkin'],'2026-11-01');self.assertEqual(len(clone['photos']),2)
  for p in clone['photos']:
   old=next(o for o in original['photos'] if o['kind']==p['kind']);self.assertNotEqual(p['id'],old['id']);self.assertEqual(p['memo'],old['memo']);self.assertEqual((MEDIA/(p['id']+'.jpg')).read_bytes(),(MEDIA/(old['id']+'.jpg')).read_bytes())
  self.client.delete('/api/records/'+newid,headers=self.headers)
  for p in original['photos']:self.assertTrue((MEDIA/(p['id']+'.jpg')).exists())
 def test_clone_failure_rolls_back_record_and_files(self):
  source=self.record();image=io.BytesIO();Image.new('RGB',(10,10),'red').save(image,'PNG');image.seek(0)
  self.client.post('/api/records/'+source+'/photos/gallery',data={'photos':(image,'image.png')},headers=self.headers);files=set(MEDIA.iterdir())
  with patch('app.shutil.copyfile',side_effect=OSError('test copy failure')),self.assertLogs(app.logger,level='ERROR'):
   response=self.client.post('/api/records',json={'clone_from':source,'name':'복제'},headers=self.headers)
  self.assertEqual(response.status_code,500);self.assertEqual(set(MEDIA.iterdir()),files);self.assertEqual(len(self.client.get('/api/state').json['records']),1)
  self.assertEqual(self.client.post('/api/records',json={'clone_from':'missing','name':'복제'},headers=self.headers).status_code,400)
 def test_bulk_delete_only_selected_records_and_photos(self):
  first=self.record(name='선택 1');second=self.record(name='선택 2');keep=self.record(name='유지');photos={}
  for ident in (first,second,keep):
   image=io.BytesIO();Image.new('RGB',(10,10),'blue').save(image,'PNG');image.seek(0);self.client.post('/api/records/'+ident+'/photos/gallery',data={'photos':(image,'image.png')},headers=self.headers)
  for record in self.client.get('/api/state').json['records']:photos[record['id']]=record['photos'][0]['id']
  self.assertEqual(self.client.post('/api/records/bulk-delete',json={'ids':[first]}).status_code,403)
  self.assertEqual(self.client.post('/api/records/bulk-delete',json={'ids':[]},headers=self.headers).status_code,400)
  response=self.client.post('/api/records/bulk-delete',json={'ids':[first,first,second,'missing']},headers=self.headers);self.assertEqual(response.status_code,200);self.assertEqual(response.json['deleted'],2)
  records=self.client.get('/api/state').json['records'];self.assertEqual([r['id'] for r in records],[keep]);self.assertFalse((MEDIA/(photos[first]+'.jpg')).exists());self.assertFalse((MEDIA/(photos[second]+'.jpg')).exists());self.assertTrue((MEDIA/(photos[keep]+'.jpg')).exists())
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
 def test_platform_defaults_addition_and_old_client_preservation(self):
  s=self.client.get('/api/state').json['settings'];self.assertEqual(s['platforms'],['홈페이지','캠핏','땡큐캠핑','네이버','캠핑톡'])
  s['platforms'].append('새 예약 플랫폼');self.assertEqual(self.client.put('/api/settings',json=s,headers=self.headers).status_code,200)
  previous_client=json.loads(json.dumps(DEFAULTS));previous_client.pop('platforms');self.assertEqual(self.client.put('/api/settings',json=previous_client,headers=self.headers).status_code,200)
  self.assertIn('새 예약 플랫폼',self.client.get('/api/state').json['settings']['platforms'])
  s['platforms'].append('캠핏');self.assertEqual(self.client.put('/api/settings',json=s,headers=self.headers).status_code,400)
 def test_platform_delete_order_concurrency_and_restore(self):
  ident=self.record(platform='캠핏');settings=self.client.get('/api/state').json['settings']
  concurrent=json.loads(json.dumps(settings));concurrent['platforms'].append('동시 추가');self.assertEqual(self.client.put('/api/settings',json=concurrent,headers=self.headers).status_code,200)
  settings['platforms']=['캠핑톡','네이버','땡큐캠핑','홈페이지'];settings['platform_order']=settings['platforms'][:];settings['platform_remove']=['캠핏']
  self.assertEqual(self.client.put('/api/settings',json=settings,headers=self.headers).status_code,200)
  state=self.client.get('/api/state').json;self.assertEqual(state['settings']['platforms'],['캠핑톡','네이버','땡큐캠핑','홈페이지','동시 추가']);self.assertEqual(state['records'][0]['platform'],'캠핏')
  old=json.loads(json.dumps(DEFAULTS));self.assertEqual(self.client.put('/api/settings',json=old,headers=self.headers).status_code,200);self.assertNotIn('캠핏',self.client.get('/api/state').json['settings']['platforms'])
  restored=self.client.get('/api/state').json['settings'];restored['platforms'].append('캠핏');restored['platform_add']=['캠핏'];restored['platform_order']=restored['platforms'][:]
  self.assertEqual(self.client.put('/api/settings',json=restored,headers=self.headers).status_code,200);self.assertIn('캠핏',self.client.get('/api/state').json['settings']['platforms'])
  empty=self.client.get('/api/state').json['settings'];empty['platform_remove']=empty['platforms'][:];empty['platforms']=[];empty['platform_order']=[]
  self.assertEqual(self.client.put('/api/settings',json=empty,headers=self.headers).status_code,200);self.assertEqual(self.client.get('/api/state').json['settings']['platforms'],[]);self.assertEqual(self.client.get('/api/state').json['records'][0]['id'],ident)
 def test_backup_excludes_pairing_keys(self):
  self.record();r=self.client.get('/api/backup');self.assertEqual(r.status_code,200)
  with zipfile.ZipFile(io.BytesIO(r.data)) as z:
   data=json.loads(z.read('journal.json'));self.assertEqual(len(data['records']),1);self.assertNotIn('mobile',data['settings']);self.assertNotIn('devices',data)
if __name__=='__main__':unittest.main()
