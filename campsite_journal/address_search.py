"""NAVER Maps address lookup. API credentials never leave the server."""
import json,os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def credentials():
 try:opts=json.loads(Path(os.getenv('JOURNAL_OPTIONS','/data/options.json')).read_text())
 except (OSError,ValueError):opts={}
 return (str(opts.get('naver_client_id','')).strip(),str(opts.get('naver_client_secret','')).strip())

def search(query):
 client_id,secret=credentials()
 if not client_id or not secret:
  return {'error':'네이버 주소 검색을 사용하려면 HA → 설정 → 앱 → 캠핑장 기록 → 구성에서 네이버 Maps Client ID와 Client Secret을 입력하고 앱을 재시작해주세요.','code':'naver_not_configured'},503
 query=query.strip()
 if not 2<=len(query)<=200:
  return {'error':'검색할 도로명주소 또는 지번주소를 2~200자로 입력해주세요.'},400
 url='https://maps.apigw.ntruss.com/map-geocode/v2/geocode?'+urlencode({'query':query,'count':20,'language':'kor'})
 req=Request(url,headers={'X-NCP-APIGW-API-KEY-ID':client_id,'X-NCP-APIGW-API-KEY':secret,'Accept':'application/json'})
 try:
  with urlopen(req,timeout=10) as r:raw=json.load(r)
 except HTTPError as e:
  if e.code in (401,403):return {'error':'네이버 인증키와 Maps의 Geocoding 사용 권한을 확인해주세요.'},502
  if e.code==429:return {'error':'네이버 검색 사용 한도에 도달했습니다. 잠시 후 다시 검색해주세요.'},429
  return {'error':'네이버 주소 검색에 연결하지 못했습니다. 잠시 후 다시 검색해주세요.'},502
 except (URLError,TimeoutError,OSError,ValueError):
  return {'error':'네이버 주소 검색에 연결하지 못했습니다. 잠시 후 다시 검색해주세요.'},502
 if raw.get('status')!='OK':return {'error':'네이버에서 주소 검색을 처리하지 못했습니다.'},502
 results=[]
 for a in raw.get('addresses',[])[:20]:
  try:lat=float(a['y']);lng=float(a['x'])
  except (KeyError,ValueError,TypeError):continue
  if not -90<=lat<=90 or not -180<=lng<=180:continue
  road=str(a.get('roadAddress') or '');jibun=str(a.get('jibunAddress') or '')
  if not road and not jibun:continue
  results.append({'address':road or jibun,'road_address':road,'jibun_address':jibun,'lat':lat,'lng':lng})
 return {'results':results,'provider':'NAVER Maps'},200
