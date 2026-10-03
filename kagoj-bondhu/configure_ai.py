"""Run locally once: python configure_ai.py. Saves credentials only to .env.
Lists models available to YOUR Gemini API key; never assumes that a sample ID is available.
"""
import getpass
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parent

def list_models(key):
    models=[]; token=None
    for _ in range(10):
        query={'pageSize':100}
        if token: query['pageToken']=token
        req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models?'+urllib.parse.urlencode(query),headers={'x-goog-api-key':key})
        with urllib.request.urlopen(req,timeout=30) as r: payload=json.load(r)
        models.extend(m for m in payload.get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]))
        token=payload.get('nextPageToken')
        if not token:break
    return models

def choose(models,prompt,allow_none=False):
    for i,m in enumerate(models,1): print(f"{i}. {m['name'].removeprefix('models/')} — {m.get('displayName','')}")
    while True:
        value=input(prompt).strip()
        if allow_none and not value:return ''
        if value.isdigit() and 1<=int(value)<=len(models):return models[int(value)-1]['name'].removeprefix('models/')
        print('Enter one of the displayed numbers.')

def main():
    old=dotenv_values(ROOT/'.env')
    key=old.get('GEMINI_API_KEY') or getpass.getpass('Paste your Gemini API key (hidden): ').strip()
    key=key.strip()
    if not key or any(c.isspace() for c in key):raise SystemExit('API key is empty or contains whitespace.')
    try:models=list_models(key)
    except Exception:raise SystemExit('Could not list models. Check the key, internet access and API availability.')
    vision=[m for m in models if 'tts' not in m['name'].lower() and not any(x in m['name'].lower() for x in ('embedding','imagen','veo','lyria'))]
    tts=[m for m in models if 'tts' in m['name'].lower()]
    if not vision:raise SystemExit('No generateContent models available to this key.')
    print('\nChoose a vision-capable Flash/Pro model for reading and explanations:')
    model=choose(vision,'Model number: ')
    print('\nChoose a TTS model for Bangla voice (optional; uses your API quota):')
    audio=choose(tts,'TTS model number, or Enter to use device speech: ',True) if tts else ''
    values=dict(old)|{'GEMINI_API_KEY':key,'GEMINI_MODEL':model,'GEMINI_TTS_MODEL':audio,'PROVIDER':'gemini','MOCK_EXTRACTION':'0','AI_EXPLANATIONS':'1','TTS_PROVIDER':'gemini' if audio else 'browser'}
    text=(ROOT/'.env.example').read_text()
    lines=[];seen=set()
    for line in text.splitlines():
        if line and not line.startswith('#') and '=' in line:
            name=line.split('=',1)[0];seen.add(name)
            value=values.get(name)
            if value is not None:line=name+'='+str(value)
        lines.append(line)
    (ROOT/'.env').write_text('\n'.join(lines)+'\n')
    print('\nSaved .env. Run python run.py, or press F5 in VS Code. No API key was printed.')
if __name__=='__main__':main()
