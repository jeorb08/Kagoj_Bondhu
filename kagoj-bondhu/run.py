"""Run from any directory: python run.py. Uses local .env; keys never enter the frontend."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
root = Path(__file__).resolve().parent
load_dotenv(root / '.env', override=True)
os.environ.setdefault('OMP_NUM_THREADS', '2')
sys.path.insert(0, str(root / 'backend'))
if __name__ == '__main__':
    import uvicorn
    print('Kagoj Bondhu photo-recovery-v2')
    print('Settings file:', root / '.env')
    print('Reading model:', os.getenv('GEMINI_MODEL', '').strip() or '(not configured)')
    uvicorn.run('app.main:app', host='127.0.0.1', port=int(os.getenv('PORT','8000')))
