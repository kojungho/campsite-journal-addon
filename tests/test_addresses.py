import io,json,unittest
from unittest.mock import patch
from urllib.error import HTTPError
import test_journal
import address_search
class AddressTest(unittest.TestCase):
 def test_missing_keys_and_auth_guard(self):
  with patch('address_search.credentials',return_value=('','')):
   r=test_journal.app.test_client().get('/api/addresses?q=분당구');self.assertEqual(r.status_code,503);self.assertEqual(r.json['code'],'naver_not_configured')
   r=test_journal.app.test_client().get('/api/addresses?q=분당구',environ_overrides={'journal.entrypoint':'external','SERVER_PORT':'8098'});self.assertEqual(r.status_code,401)
 def test_naver_response_and_server_only_credentials(self):
  raw={'status':'OK','addresses':[{'roadAddress':'경기도 성남시 분당구 불정로 6','jibunAddress':'경기도 성남시 분당구 정자동 178-1','x':'127.105','y':'37.359'}]}
  with patch('address_search.credentials',return_value=('test-id','test-secret')),patch('address_search.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())) as call:
   result,status=address_search.search('분당구 불정로 6');self.assertEqual(status,200);a=result['results'][0];self.assertEqual(a['address'],raw['addresses'][0]['roadAddress']);self.assertEqual(a['lat'],37.359);self.assertEqual(a['lng'],127.105)
   req=call.call_args.args[0];self.assertTrue(req.full_url.startswith('https://maps.apigw.ntruss.com/'));self.assertNotIn('test-secret',req.full_url);self.assertNotIn('test-secret',json.dumps(result))
 def test_failure_is_actionable_and_does_not_leak_secrets(self):
  with patch('address_search.credentials',return_value=('test-id','test-secret')),patch('address_search.urlopen',side_effect=HTTPError('https://maps.apigw.ntruss.com/',403,'secret',{},None)):
   result,status=address_search.search('분당구');self.assertEqual(status,502);self.assertIn('인증키',result['error']);self.assertNotIn('test-secret',result['error'])
 def test_road_fallback_and_invalid_coordinate(self):
  raw={'status':'OK','addresses':[{'jibunAddress':'강원도 춘천시 1-1','x':'127','y':'37'},{'roadAddress':'invalid','x':'999','y':'37'}]}
  with patch('address_search.credentials',return_value=('id','secret')),patch('address_search.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
   result,status=address_search.search('춘천시 1-1');self.assertEqual(len(result['results']),1);self.assertEqual(result['results'][0]['address'],'강원도 춘천시 1-1')
