"""Cloud Bangla/English TTS with Gemini. Returns in-memory WAV; no audio is stored."""
import base64
import io
import os
import re
import wave
from .ai_client import gemini_request, AIUnavailable


def configured():
    return os.getenv('TTS_PROVIDER','gemini')=='gemini' and bool(os.getenv('GEMINI_API_KEY')) and bool(os.getenv('GEMINI_TTS_MODEL'))


def synthesize(text, language='bn'):
    if not configured(): raise AIUnavailable('speech_not_configured')
    if not text.strip() or len(text.encode('utf-8')) > 12000:
        raise ValueError('Speech text must be nonempty and at most 12000 UTF-8 bytes')
    voice = os.getenv('GEMINI_TTS_VOICE','Kore')
    language_name = 'Bangla (Bengali)' if language=='bn' else 'English'
    model = os.getenv('GEMINI_TTS_MODEL','')
    version = re.match(r'gemini-(\d+)\.(\d+)',model)
    modern = bool(version and tuple(map(int,version.groups())) >= (3,8))
    # Newer TTS uses verbatim transcript + style metadata; older preview models
    # accept a reading instruction and prebuiltVoiceConfig. Both audio formats work.
    part = {'text':text,'speech_metadata':{'style':f'Speak {language_name}, slowly, clearly and kindly.'}} if modern else {'text':f'Read verbatim in {language_name}, slowly and clearly. Do not add commentary.\n\n{text}'}
    voice_config = {'voice':voice} if modern else {'prebuiltVoiceConfig':{'voiceName':voice}}
    body = {
        'contents':[{'role':'user','parts':[part]}],
        'generationConfig':{'responseModalities':['AUDIO'],
            'speechConfig':{'voiceConfig':voice_config}}
    }
    payload = gemini_request(body,model=os.getenv('GEMINI_TTS_MODEL'))
    parts = [p for c in payload.get('candidates',[]) for p in c.get('content',{}).get('parts',[])]
    block = next((p.get('inlineData') or p.get('inline_data') for p in parts if p.get('inlineData') or p.get('inline_data')),None)
    if not block or not block.get('data'): raise AIUnavailable('speech_no_audio')
    try: audio = base64.b64decode(block['data'],validate=True)
    except ValueError: raise AIUnavailable('speech_invalid_audio') from None
    mime = block.get('mimeType',block.get('mime_type','')).lower()
    if audio.startswith(b'RIFF') and audio[8:12]==b'WAVE':
        return audio, 'audio/wav'
    if 'wav' in mime: raise AIUnavailable('speech_invalid_wav')
    if 'l16' not in mime and 'pcm' not in mime:
        raise AIUnavailable('speech_unsupported_audio_format')
    if len(audio)%2 or not audio: raise AIUnavailable('speech_invalid_pcm')
    match = re.search(r'rate=(\d+)',mime)
    rate = int(match.group(1)) if match else 24000
    if rate not in (8000,16000,22050,24000,44100,48000): raise AIUnavailable('speech_invalid_sample_rate')
    buf = io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(audio)
    return buf.getvalue(), 'audio/wav'
