#!/usr/bin/env python3
"""ClaimPilot AI: zero-dependency local server and secure OpenAI proxy."""
import base64
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '8000'))
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
MAX_REQUEST = 18 * 1024 * 1024
SYSTEM = '''You are ClaimPilot AI, an industrial quality engineer assistant for automotive customer complaints. Return ONLY valid JSON with fields: summary (string), severity (one of Nízka, Stredná, Vysoká, Kritická), category (string), confidence (integer 0-100 indicating confidence in extraction, not root cause), extracted (array of objects {label,value,source}), missing (array of strings), next_steps (array of strings), hypotheses (array of strings), eight_d (object with keys D1,D2,D3,D4,D5,D6,D7,D8, each string), warnings (array of strings). Write all text in Slovak. Extract only supported facts. Never invent customer, part number, dates, batch IDs, measurements or root causes. If information is unavailable, explicitly say 'Neznáme – vyžaduje overenie'. Clearly label D4 root causes as unverified hypotheses; do not claim verified corrective actions or completed steps. D1-D8 is a DRAFT, not an approved final report. Consider image evidence if present. Be succinct and actionable.'''

class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            data = (ROOT / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)
        elif self.path == '/api/health':
            self.send_json(200, {'ok': True, 'configured': bool(os.getenv('OPENAI_API_KEY')),'model': MODEL})
        else:
            self.send_json(404, {'error': 'Nenájdené'})

    def do_POST(self):
        if self.path != '/api/analyze':
            return self.send_json(404, {'error': 'Nenájdené'})
        if self.headers.get('Origin'):
            # Same-origin requests only. No permissive CORS headers.
            from urllib.parse import urlparse
            origin = urlparse(self.headers['Origin'])
            host = self.headers.get('Host', '')
            if origin.netloc != host or origin.scheme not in ('http', 'https'):
                return self.send_json(403, {'error': 'Nepovolený pôvod požiadavky'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_REQUEST:
                return self.send_json(413, {'error': 'Požiadavka je príliš veľká (max 18 MB).'})
            payload = json.loads(self.rfile.read(length))
            description = str(payload.get('description', '')).strip()[:12000]
            files = payload.get('files', [])
            if not isinstance(files, list) or len(files) > 4:
                return self.send_json(400, {'error': 'Maximálne 4 súbory.'})
            if not description and not files:
                return self.send_json(400, {'error': 'Zadajte opis alebo priložte súbor.'})
            key = os.getenv('OPENAI_API_KEY')
            if not key:
                return self.send_json(503, {'error': 'Na serveri chýba OPENAI_API_KEY.'})
            content = [{'type': 'input_text', 'text': 'Opis reklamácie:\n' + (description or '(bez textu)')}]
            for item in files:
                mime = item.get('type', '')
                name = str(item.get('name', 'document'))[:120].replace('/', '_').replace('\\', '_')
                data = item.get('data', '')
                if mime not in ('image/jpeg', 'image/png', 'image/webp', 'application/pdf') or not isinstance(data, str):
                    return self.send_json(400, {'error': 'Podporované sú JPG, PNG, WEBP a PDF.'})
                raw = base64.b64decode(data, validate=True)
                if len(raw) > 5 * 1024 * 1024:
                    return self.send_json(413, {'error': 'Každý súbor môže mať max. 5 MB.'})
                if mime == 'application/pdf':
                    if not raw.startswith(b'%PDF-'):
                        return self.send_json(400, {'error': 'Neplatný PDF súbor.'})
                    content.append({'type': 'input_file', 'filename': name if name.lower().endswith('.pdf') else name+'.pdf', 'file_data': 'data:application/pdf;base64,' + data})
                else:
                    magic_ok = (mime == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (mime == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime == 'image/webp' and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP')
                    if not magic_ok:
                        return self.send_json(400, {'error': 'Neplatný obrázok.'})
                    content.append({'type': 'input_image', 'image_url': 'data:' + mime + ';base64,' + data, 'detail': 'auto'})
            req_body = json.dumps({'model': MODEL, 'instructions': SYSTEM, 'input': [{'role': 'user', 'content': content}], 'text': {'format': {'type': 'json_object'}}, 'max_output_tokens': 3200}).encode()
            request = Request('https://api.openai.com/v1/responses', data=req_body, headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'}, method='POST')
            try:
                with urlopen(request, timeout=90) as response:
                    result = json.load(response)
            except HTTPError as exc:
                # Do not leak API credentials or upstream response bodies.
                return self.send_json(502, {'error': f'AI služba vrátila HTTP {exc.code}. Skontrolujte model, kredit a API kľúč.'})
            except (URLError, TimeoutError):
                return self.send_json(504, {'error': 'AI služba neodpovedá. Skúste to znova.'})
            parts = [part.get('text', '') for output in result.get('output', []) if output.get('type') == 'message' for part in output.get('content', []) if part.get('type') == 'output_text']
            if not parts:
                return self.send_json(502, {'error': 'Model nevrátil textový výsledok. Skúste kratší vstup.'})
            analysis = json.loads(''.join(parts))
            if not isinstance(analysis, dict) or not isinstance(analysis.get('eight_d'), dict):
                return self.send_json(502, {'error': 'Neúplný výsledok modelu. Skúste to znova.'})
            self.send_json(200, {'analysis': analysis})
        except (ValueError, TypeError, KeyError, UnicodeError):
            self.send_json(400, {'error': 'Neplatné vstupné údaje alebo odpoveď modelu.'})
        except Exception:
            self.send_json(500, {'error': 'Interná chyba servera.'})

if __name__ == '__main__':
    print(f'ClaimPilot AI → http://{HOST}:{PORT} | AI model: {MODEL}')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
