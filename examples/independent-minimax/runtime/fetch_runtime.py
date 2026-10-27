"""Retrieve the official source bundle, accepting only the recorded content hash."""
from pathlib import Path
import json,hashlib,urllib.request,os,argparse,tempfile
R=Path(__file__).resolve().parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out',type=Path,required=True,help='Task cache path; do not write into the installed Skill')
ap.add_argument('--source-file',type=Path,help='Verify a previously archived official bundle without network')
args=ap.parse_args()
pin=json.loads((R/'graph-runtime.json').read_text())
request=urllib.request.Request(pin.get('download_url',pin['source_url']),headers={'Accept':pin.get('download_accept','*/*'),'User-Agent':'technical-architecture-diagrams-skill'})
b=args.source_file.read_bytes() if args.source_file else urllib.request.urlopen(request,timeout=60).read()
h=hashlib.sha256(b).hexdigest()
if h!=pin['sha256']:raise RuntimeError('Rolling upstream source changed; do not silently replace pinned runtime: '+h)
out=args.out.resolve();out.parent.mkdir(parents=True,exist_ok=True)
with tempfile.NamedTemporaryFile(dir=out.parent,delete=False) as f:
 f.write(b);f.flush();os.fsync(f.fileno());tmp=f.name
os.replace(tmp,out)
print('Official draw.io Graph bundle verified',pin['version'],h)
