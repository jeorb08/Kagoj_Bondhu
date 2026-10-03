"""Safe local AI check. Uses the adjacent .env; never prints credentials."""
import base64
import sys
from pathlib import Path
import run
from app import extract
from app.ai_client import AIUnavailable, gemini_request, public_error


def main():
    print('Settings file:', run.root / '.env')
    print('Provider:', extract.provider())
    import os
    print('Reading model:', os.getenv('GEMINI_MODEL','').strip())
    try:
        gemini_request({'contents':[{'parts':[{'text':'Reply with OK'}]}]})
        print('Basic request: passed')
        image_path=Path(sys.argv[1]) if len(sys.argv)>1 else run.root/'demo'/'consistent.jpg'
        media={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp'}.get(image_path.suffix.lower())
        if not media:raise ValueError('Use a JPEG, PNG or WebP sample.')
        image='data:'+media+';base64,'+base64.b64encode(image_path.read_bytes()).decode()
        result=extract.read_document('payslip',image)
        print('Photo extraction: passed')
        print('Fields read:', sum(f['value'] is not None for f in result['fields'].values()))
        print('No field contents or credentials printed.')
    except AIUnavailable as e:
        print('AI failure:', public_error(e));return 1
    except Exception as e:
        print('Local failure:',type(e).__name__);return 1
    return 0

if __name__=='__main__':sys.exit(main())
