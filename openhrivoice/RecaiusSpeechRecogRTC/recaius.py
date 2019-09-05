#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
import time,wave
import math
import json
import urllib
import urllib.request, urllib.error
import cookielib

import base64


class RecaiusAsr():
  def __init__(self, service_id="", passwd=""):
     self._baseAuthUrl="https://api.recaius.jp/auth/v2/"
     self._baseAsrUrl="https://api.recaius.jp/asr/v2/"
     self._service_id=service_id
     self._passwd=passwd
     self._token = ''
     self._uuid = ''
     self._vid=1
     self._silence = getWavData("silence.wav")
     self._expiry=0
     self._boundary = "----Boundary"

     opener = urllib.request.build_opener(urllib.request.HTTPSHandler(debuglevel=0),
                             urllib.request.HTTPCookieProcessor(cookielib.CookieJar()))
     urllib.request.install_opener(opener)

  def setAccount(self, service_id, passwd):
     self._service_id=service_id
     self._passwd=passwd


  #-------- Recaius Authorization
  def requestAuthToken(self, ex_sec=600):
     url = self._baseAuthUrl+'tokens'
     headers = {'Content-Type' : 'application/json' }
     data = { "speech_recog_jaJP": { "service_id" : self._service_id, "password" : self._passwd}, "expiry_sec" : ex_sec }

     request = urllib.request.Request(url, data=json.dumps(data), headers=headers)
     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print ('Error code:', e.code)
       return None
     except urllib.error.URLError as e:
       print ('URLErroe reason:', e.reason)
       return None
     else:
       response = result.read()
       res = response.decode('utf-8')
       self._expiry = time.time() + ex_sec
       print (res)
       data=json.loads(res)
       self._token=data['token']
       return self._token

  def refreshAuthToken(self, ex_sec=600):
     url = self._baseAuthUrl+'tokens'
     headers = {'Content-Type' : 'application/json', 'X-Token' : self._token }

     data = { "speech_recog_jaJP": { "service_id" : self._service_id, "password" : self._passwd}, "expiry_sec" : ex_sec }

     request = urllib.request.Request(url, data=json.dumps(data), headers=headers)
     request.get_method = lambda : 'PUT'
     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print( 'Error code:', e.code)
       return -1
     except urllib.error.URLError as e:
       print ('URLErroe reason:', e.reason)
       return -1
     else:
       response = result.read()
       res = response.decode('utf-8')
       self._expiry = time.time() + ex_sec
       #print (res)
       return self._expiry

    
  def checkAuthToken(self):
     query_string = {'service_name' : 'speech_recog_jaJP'}
     url = '{0}?{1}'.format(self._baseAuthUrl+'tokens', urllib.urlencode(query_string))
     headers = {'Content-Type' : 'application/json', 'X-Token' : self._token }

     request = urllib.request.Request(url, headers=headers)
     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print ('Error code:', e.code)
       return -1
     except urllib.error.URLError as e:
       print ('URLErroe reason:', e.reason)
       return -1
     else:
       response = result.read()
       res = response.decode('utf-8')
       data=json.loads(res)
       return data['remaining_sec']

  #-------- Voice Recognition
  def startVoiceRecogSession(self, model=1):
     url = self._baseAsrUrl+'voices'
     headers = {'Content-Type' : 'application/json', 'X-Token' : self._token }

     data = { "audio_type": "audio/x-linear",
              "result_type": "nbest",
              #"push_to_talk": True,
              "model_id": model,
              "comment": "Start" }

     request = urllib.request.Request(url, data=json.dumps(data), headers=headers)
     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print ('Error code:', e.code)
       print ('Reason:', e.reason)
       return False
     except urllib.error.URLError as e:
       print ('URLErroe reason:', e.reason)
       return False
     else:
       response = result.read()
       res = response.decode('utf-8')
       data=json.loads(res)
       self._uuid = data['uuid']
       self._boundary = "----Boundary"+base64.b64encode(self._uuid)
       return True

  def endVoiceRecogSession(self):
     url = self._baseAsrUrl+'voices/'+self._uuid
     headers = {'X-Token' : self._token }

     request = urllib.request.Request(url, headers=headers)
     request.get_method = lambda : 'DELETE'
     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print ('Error code:', e.code)
       print ('Reason:', e.reason)
       return False
     except urllib.error.URLError as e:
       print( 'URLErroe reason:', e.reason)
       return False
     else:
       response = result.read()
       res = response.decode('utf-8')
       if res : print (res)
       return True

  def getVoiceRecogResult(self, data):
      #data = self._silence+data
      data += self._silence+self._silence
      voice_data = divString(data, 16364)
      #voice_data = divString(data, 32728)
      self._vid=0

      for d in voice_data:
        self._vid += 1
        res = self.sendSpeechData(self._vid, d)
        if res :
          data=json.loads(res)
          for d in data:
            if d['type'] == 'RESULT' :
              return d
          print (res)
      return self.flushVoiceRecogResult()

  def sendSpeechData(self, vid, data):
     url = self._baseAsrUrl+'voices/'+self._uuid
     headers = {'Content-Type' : 'multipart/form-data','X-Token' : self._token }

     form_data = ""
     form_data += self._boundary+"\r\n"
     form_data += "Content-Disposition: form-data;name=\"voice_id\"\r\n\r\n"
     form_data += str(vid)+"\r\n"
     form_data += self._boundary+"\r\n"
     form_data += "Content-Disposition: form-data;name=\"voice\"\r\n"
     form_data += "Content-Type: application/octet-stream\r\n\r\n"
     form_data += data
     form_data += "\r\n"
     form_data += self._boundary+"\r\n"

     request = urllib.request.Request(url)
     request.add_header( 'X-Token', self._token )
     request.add_header( 'Content-Type', 'multipart/form-data')
     request.add_data(bytearray(form_data))

     request.get_method = lambda : 'PUT'

     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print ('Error code:', e.code)
       print ('Reason:', e.reason)
       return False
     except urllib.error.URLError as e:
       print ('URLErroe reason:', e.reason)
       return False
     else:
       response = result.read()
       res = response.decode('utf-8')
       if res :
         return res
       return False

  def flushVoiceRecogResult(self):
     url = self._baseAsrUrl+'voices/'+self._uuid+"/flush"
     headers = {'Content-Type' : 'application/json', 'X-Token' : self._token }

     data = { "voice_id": self._vid }

     request = urllib.request.Request(url, data=json.dumps(data), headers=headers)
     request.get_method = lambda : 'PUT'

     try:
       result = urllib.urlopen(request)
     except urllib.error.HTTPError as e:
       print( 'Error code:', e.code)
       print( 'Reason:', e.reason)
       return False
     except urllib.error.URLError as e:
       print( 'URLErroe reason:', e.reason)
       return False
     else:
       response = result.read()
       res = response.decode('utf-8')
       return res

  def request_speech_recog(self, data):
    result = ""
    self.requestAuthToken()
    recaius = self.startVoiceRecogSession()
    if recaius :
      result = self.getVoiceRecogResult(data)
      self.endVoiceRecogSession()
    return result


def getWavData(fname):
    try:
        f = wave.open(fname)
        data = f.readframes(f.getnframes())
        f.close()
        return data
    except:
        return ""

def divString(s, n):
  ll=len(s)
  res = []
  for x in range(int(math.ceil(float(ll) / n))):
    res.append( s[ x*n : x*n + n ] )

  return res


#
#  Main
#
if __name__ == '__main__':
  import glob
  recaius = RecaiusAsr('haraisao_MAj34mD8GZ', 'isao11038867')
  files = glob.glob('log/*.wav')
  files.sort()

  for f in files:
    print (f)
    data = getWavData(f)

    result = recaius.request_speech_recog(data)
    if result :
      try:
        data = json.loads( result )
        i=1
        for d in data[0]['result'] :
          if 'confidence' in d :
            score=str(d['confidence'])
          else:
            score="0.0"
          print ("#"+str(i)+":"+d['str']+"  ("+score+")")
          #print d
          i+=1
      except:
        print( result)
    else:
      print ("No Result")
    print( "")

