"""Inventory sky-flagged JK1 campaign surfaces and decode private, palette-correct MAT references.

Usage: python tools/sky_references.py GAME OUTPUT
Original textures are written only to the explicitly supplied private scratch directory.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

from PIL import Image, ImageDraw
from gob import read_index


def sections(text):
    return {part.splitlines()[0].strip().lower(): '\n'.join(part.splitlines()[1:])
            for part in re.split(r'(?im)^section:', text.replace('\r', ''))[1:]}


def decode_mat(data):
    header = struct.unpack_from('<4s18I', data)
    magic, revision, kind, cel_count, texture_count, is16bit, bpp = header[:7]
    if magic != b'MAT ' or revision != 50 or bpp != 8:
        raise ValueError(f'Unsupported MAT: {header[:7]}')
    pos, cels = 76, []
    for _ in range(cel_count):
        cel = struct.unpack_from('<6I', data, pos); pos += 24
        texture = None
        if cel[0] & 8:
            texture = struct.unpack_from('<4I', data, pos)[3]; pos += 16
        cels.append((texture, cel[1]))
    textures = []
    for _ in range(texture_count):
        w, h, alpha, unknown, transparent, mips = struct.unpack_from('<6I', data, pos); pos += 24
        first = data[pos:pos + w*h]
        if len(first) != w*h:
            raise ValueError('Truncated MAT pixels')
        textures.append(dict(width=w, height=h, alpha=alpha, transparent=transparent, mipmaps=mips, pixels=first))
        pos += sum(max(1, w >> level)*max(1, h >> level) for level in range(mips))
    palette = data[pos:pos+768] if kind & 1 else None
    if palette is not None:
        pos += 768
    if pos != len(data):
        raise ValueError(f'MAT size mismatch: decoded {pos}, archive {len(data)}')
    return kind, cels, textures, palette


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    # The owning Helm budget check applies even when the utility is rerun independently.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'helm'))
    from dashboard.retention import require_storage_budget
    require_storage_budget(args.output, 32*1024*1024)
    args.output.mkdir(parents=True, exist_ok=True)
    references = args.output / 'references'; references.mkdir(exist_ok=True)
    archive = {}
    for folder, pattern in [('Resource', '*.gob'), ('Episode', 'JK1.GOB')]:
        for gob in sorted((args.game/folder).glob(pattern)):
            for name, offset, size in read_index(gob):
                archive[name.lower()] = (gob, offset, size)
    def read(name):
        path, offset, size = archive[name.lower()]
        with path.open('rb') as stream:
            stream.seek(offset); data = stream.read(size)
        if len(data) != size:
            raise ValueError(f'Truncated archive entry {name}')
        return data
    episode = read('episode.jk').decode('latin1')
    levels = list(dict.fromkeys(re.findall(r'(?im)^\d+:\s+\d+\s+\d+\s+LEVEL\s+(\S+)', episode.lower())))
    uses, excluded, coverage = defaultdict(list), [], []
    for level in levels:
        sec = sections(read('jkl\\'+level).decode('latin1'))
        mats = {int(i):name.lower() for i,name in re.findall(r'(?m)^(\d+):\s+(\S+\.mat)', sec['materials'])}
        geo = sec['georesource']
        palettes = {int(i):name.lower() for i,name in re.findall(r'(?m)^(\d+):\s+(\S+\.cmp)', geo)}
        palette_for_surface = {}
        sector_for_surface = {}
        sectors = re.split(r'(?im)^SECTOR\s+(\d+)\s*$',sec['sectors'])
        sector_ids = [int(sectors[i]) for i in range(1,len(sectors),2)]
        sector_index = 0
        for sector in re.split(r'(?im)^SECTOR\s+\d+\s*$',sec['sectors'])[1:]:
            palette_id = int(re.search(r'(?im)^COLORMAP\s+(\d+)',sector)[1])
            first, count = map(int,re.search(r'(?im)^SURFACES\s+(\d+)\s+(\d+)',sector).groups())
            box_match = re.search(r'(?im)^COLLIDEBOX\s+([^\n]+)',sector)
            bounds = list(map(float,box_match[1].split())) if box_match else None
            for surface in range(first,first+count):
                palette_for_surface[surface] = palettes[palette_id]
                sector_for_surface[surface] = (sector_ids[sector_index],bounds)
            sector_index += 1
        vertex_text = geo.split('World vertices',1)[1].split('World texture vertices',1)[0]
        vertices = {int(v[0][:-1]):list(map(float,v[1:4])) for line in vertex_text.splitlines()
                    if len(v:=line.split())==4 and re.fullmatch(r'\d+:',v[0])}
        count = 0
        for line in geo.split('World surfaces',1)[1].splitlines()[1:]:
            fields=line.split()
            if len(fields)<10 or not re.fullmatch(r'\d+:',fields[0]): continue
            surface, mat, flags = int(fields[0][:-1]),int(fields[1]),int(fields[2],0)
            if not flags & 0x600: continue
            count += 1
            sector_id, bounds = sector_for_surface[surface]
            record = dict(level=level,surface=surface,sector=sector_id,flags=hex(flags),sky_flags=hex(flags & 0x600),
                          geometry=int(fields[4]),palette=palette_for_surface[surface])
            if bounds:
                origin = [(bounds[k]+bounds[k+3])/2 for k in range(3)]
                points = [vertices[int(v.split(',')[0])] for v in fields[10:10+int(fields[9])]]
                target = [sum(v[k] for v in points)/len(points) for k in range(3)]
                delta = [target[k]-origin[k] for k in range(3)]
                yaw = math.degrees(math.atan2(-delta[0],delta[1]))
                pitch = math.degrees(math.atan2(delta[2],math.hypot(delta[0],delta[1])))
                record['camera_candidate'] = dict(position=origin,target=target,pitch=pitch,yaw=yaw,
                    warp=' '.join(f'{v:.5f}' for v in [*origin,pitch,yaw,0]),
                    status='Derived from interior COLLIDEBOX center toward sky face center; not live verified')
            if mat < 0:
                excluded.append(dict(**record, reason='No material: engine sets geometry NONE'))
            else:
                uses[mats[mat]].append(record)
        coverage.append(dict(level=level,sky_flagged_surfaces=count))
    manifest = dict(levels=coverage,materials=[],excluded_surfaces=excluded,
                    scope='All episode.jk LEVEL entries, all horizon 0x200 and ceiling 0x400 surface flags; all MAT cels decoded.')
    contacts=[]
    for name, usage in sorted(uses.items()):
        mat_bytes=read('mat\\'+name)
        kind,cels,textures,embedded=decode_mat(mat_bytes)
        record=dict(material=name,archive=str(archive['mat\\'+name][0]),sha256=hashlib.sha256(mat_bytes).hexdigest(),
                    material_type=kind,cel_count=len(cels),texture_count=len(textures),uses=usage,references=[])
        if not kind & 2:
            record['excluded']='Solid-color material: engine clears sky flags'
        for cel_id,(texture_id,solid) in enumerate(cels):
            tex=textures[texture_id] if texture_id is not None else dict(width=1,height=1,pixels=bytes([solid]),mipmaps=0,alpha=0,transparent=0)
            variants={}
            for palette_name in sorted({use['palette'] for use in usage}):
                cmp=read('misc\\cmp\\'+palette_name)
                if cmp[:4]!=b'CMP ': raise ValueError(palette_name)
                palette=embedded if embedded is not None else cmp[64:832]
                image=Image.frombytes('P',(tex['width'],tex['height']),tex['pixels']);image.putpalette(palette)
                if tex['alpha']:
                    image.info['transparency']=tex['transparent']
                    image=image.convert('RGBA')
                else:
                    image=image.convert('RGB')
                digest=hashlib.sha256(image.tobytes()).hexdigest()
                if digest in variants:
                    variants[digest]['palettes'].append(palette_name);continue
                filename=f'{Path(name).stem}__cel{cel_id}__{Path(palette_name).stem}.png'
                path=references/filename;image.save(path)
                variant=dict(cel=cel_id,texture=texture_id,width=tex['width'],height=tex['height'],mipmaps=tex['mipmaps'],
                    alpha=tex['alpha'],transparent_index=tex['transparent'],palettes=[palette_name],path=str(path),rgb_sha256=digest,
                    indexed_md5=hashlib.md5(tex['pixels']).hexdigest())
                variants[digest]=variant
                contacts.append((filename,image))
            record['references'].extend(variants.values())
        candidates = [u for u in usage if 'camera_candidate' in u]
        if candidates:
            choice = candidates[0]
            record['qa'] = dict(level=choice['level'],sector=choice['sector'],surface=choice['surface'],**choice['camera_candidate'])
        if name == '03sky09k.mat':
            record['qa'] = dict(level='03katarn.jkl',warp='-0.7645 -4.738 -0.2034 0 -90 0',
                status='Existing verified capture_showcase.py sky-landscape view; tilt upward for clouds')
        record['role'] = ('starfield; retain procedural replacement' if name in ('00starry.mat','00stars2.mat')
                          else 'architectural transparent grille; exclude from sky artwork' if name == '00wgril6.mat'
                          else 'cloud sky; preserve original orientation and repeating texture mapping')
        record['projection'] = sorted({'horizon angular' if int(u['sky_flags'],16)&0x200 else 'ceiling plane' for u in usage})
        record['current_shader']='procedural star replacement' if name in ('00starry.mat','00stars2.mat') else 'original artwork; horizon uses angular remap, ceiling uses authored projection'
        manifest['materials'].append(record)
        print(name, [(r['width'],r['height'],r['cel'],r['palettes']) for r in record['references']],flush=True)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    summary = dict(scope=manifest['scope'],clouds=[{k:mat[k] for k in ('material','sha256','qa')}
        | {'references':[{key:ref[key] for key in ('cel','width','height','palettes','rgb_sha256')} for ref in mat['references']],
           'levels':sorted({u['level'] for u in mat['uses']})} for mat in manifest['materials'] if mat['role'].startswith('cloud')],
        exclusions={'procedural_stars':['00starry.mat','00stars2.mat'],
                    'architectural_grille':'00wgril6.mat: 10cargo surface494/sector49, transparent architectural grille, not cloud artwork',
                    'untextured_sky_flagged_surfaces':len(excluded)})
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    width=768;cellw=256;cellh=286
    sheet=Image.new('RGB',(width,((len(contacts)+2)//3)*cellh),(24,24,24));draw=ImageDraw.Draw(sheet)
    for i,(label,picture) in enumerate(contacts):
        x=(i%3)*cellw;y=(i//3)*cellh
        thumb=picture.copy();thumb.thumbnail((256,256),Image.Resampling.NEAREST)
        sheet.paste(thumb,(x,y));draw.text((x+3,y+258),label,fill='white')
    sheet.save(args.output/'contact-sheet.png')
    print(f'{len(levels)} levels; {len(uses)} materials; {len(contacts)} unique cel/palette images; {len(excluded)} untextured flagged surfaces')


if __name__=='__main__': main()
