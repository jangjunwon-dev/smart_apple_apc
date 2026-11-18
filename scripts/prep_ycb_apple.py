#!/usr/bin/env python3
"""YCB 013_apple 원본 GLB → Gazebo 용 정규화 GLB 변환기.

사용법 (저장소 루트에서, 원본은 저장소 밖 임시 폴더에 받을 것):
  curl -L -o /tmp/ycb/textured.glb.orig \\
    https://huggingface.co/datasets/ai-habitat/ycb/resolve/main/meshes/013_apple/google_16k/textured.glb.orig
  python3 -I scripts/prep_ycb_apple.py /tmp/ycb/textured.glb.orig
  python3 -I scripts/prep_ycb_apple.py <원본.glb> <결과.glb> [텍스처_픽셀]
기본 결과: src/apc_simulation/models/ycb_apple/meshes/ycb_apple.glb, 텍스처 1024 px

- 원본: Hugging Face ai-habitat/ycb (CC BY 4.0, 출처는 models/ATTRIBUTION.md)
  textured.glb 는 BASIS 압축 텍스처라 Gazebo 가 못 읽으므로 비압축 원본 textured.glb.orig 를 사용
- 변환 내용
  1. 축은 그대로(+z 가 꼭지 방향, object_config.json 의 up=[0,0,1])
  2. 수평 중심(x·y 범위 가운데)을 원점으로, 수평 반지름(x·y 범위 절반의 평균)을 1.0 으로 균일 축소/확대
  3. 바닥을 z = -1.0 으로 → SDF <scale>r r r</scale> 하나로 반지름 r 사과가 되고 바닥이 -r
     (apple_factory 의 collision 바닥 -r 과 일치)
  4. 텍스처 PNG 를 정사각 N px JPG(품질 90)로 줄여 GLB 하나에 다시 내장
- numpy, Pillow 만 사용 (새 의존성 없음)
"""
from __future__ import annotations

import io
import json
import os
import struct
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(
    ROOT, 'src', 'apc_simulation', 'models', 'ycb_apple', 'meshes', 'ycb_apple.glb')

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
COMPONENT_DTYPE = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
TYPE_SIZE = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}


def read_glb(path: str) -> tuple[dict, bytes]:
    data = open(path, 'rb').read()
    magic, version, _ = struct.unpack('<III', data[:12])
    if magic != GLB_MAGIC or version != 2:
        raise ValueError('glTF 2.0 GLB 파일이 아님')
    off = 12
    gltf, binary = None, b''
    while off < len(data):
        length, ctype = struct.unpack('<II', data[off:off + 8])
        chunk = data[off + 8:off + 8 + length]
        if ctype == CHUNK_JSON:
            gltf = json.loads(chunk)
        elif ctype == CHUNK_BIN:
            binary = chunk
        off += 8 + length
    if gltf is None:
        raise ValueError('JSON 청크 없음')
    return gltf, binary


def view_bytes(gltf: dict, binary: bytes, index: int) -> bytes:
    bv = gltf['bufferViews'][index]
    start = bv.get('byteOffset', 0)
    return binary[start:start + bv['byteLength']]


def read_accessor(gltf: dict, binary: bytes, index: int) -> np.ndarray:
    acc = gltf['accessors'][index]
    bv = gltf['bufferViews'][acc['bufferView']]
    dtype = np.dtype(COMPONENT_DTYPE[acc['componentType']])
    ncomp = TYPE_SIZE[acc['type']]
    stride = bv.get('byteStride', dtype.itemsize * ncomp)
    if stride != dtype.itemsize * ncomp:
        raise ValueError('interleaved 버퍼는 지원하지 않음')
    start = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    arr = np.frombuffer(binary, dtype=dtype, count=acc['count'] * ncomp, offset=start)
    return arr.reshape(acc['count'], ncomp) if ncomp > 1 else arr.copy()


def normalize(pos: np.ndarray) -> np.ndarray:
    """수평 반지름 1, 수평 중심 원점, 바닥 z=-1 로 균일 변환."""
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    center_xy = (lo[:2] + hi[:2]) / 2.0
    radius = float(np.mean((hi[:2] - lo[:2]) / 2.0))
    out = pos.astype(np.float64).copy()
    out[:, :2] -= center_xy
    out[:, 2] -= lo[2]
    out /= radius
    out[:, 2] -= 1.0
    return out.astype(np.float32)


def pad4(b: bytes, fill: bytes = b'\x00') -> bytes:
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path: str, pos: np.ndarray, nrm: np.ndarray, uv: np.ndarray,
              idx: np.ndarray, jpg: bytes, material: dict) -> None:
    parts = [pos.astype('<f4').tobytes(), nrm.astype('<f4').tobytes(),
             uv.astype('<f4').tobytes(), idx.astype('<u2').tobytes(), jpg]
    views, blob = [], b''
    for i, p in enumerate(parts):
        view = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(p)}
        if i < 3:
            view['target'] = 34962
        elif i == 3:
            view['target'] = 34963
        views.append(view)
        blob += pad4(p)
    gltf = {
        'asset': {'version': '2.0', 'generator': 'apc_ws scripts/prep_ycb_apple.py'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'ycb_apple', 'mesh': 0}],
        'meshes': [{'name': 'ycb_apple', 'primitives': [{
            'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2},
            'indices': 3, 'material': 0, 'mode': 4}]}],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3',
             'min': pos.min(axis=0).tolist(), 'max': pos.max(axis=0).tolist()},
            {'bufferView': 1, 'componentType': 5126, 'count': len(nrm), 'type': 'VEC3'},
            {'bufferView': 2, 'componentType': 5126, 'count': len(uv), 'type': 'VEC2'},
            {'bufferView': 3, 'componentType': 5123, 'count': len(idx), 'type': 'SCALAR'},
        ],
        'bufferViews': views,
        'buffers': [{'byteLength': len(blob)}],
        'images': [{'name': 'ycb_apple_texture', 'mimeType': 'image/jpeg', 'bufferView': 4}],
        'samplers': [{'wrapS': 10497, 'wrapT': 10497}],
        'textures': [{'sampler': 0, 'source': 0}],
        'materials': [material],
    }
    js = pad4(json.dumps(gltf, separators=(',', ':')).encode(), b' ')
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', GLB_MAGIC, 2, total))
        f.write(struct.pack('<II', len(js), CHUNK_JSON) + js)
        f.write(struct.pack('<II', len(blob), CHUNK_BIN) + blob)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    tex_px = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

    gltf, binary = read_glb(src)
    prims = gltf['meshes'][0]['primitives']
    if len(gltf['meshes']) != 1 or len(prims) != 1:
        raise ValueError('메시·primitive 가 1개인 GLB 만 지원')
    prim = prims[0]
    attrs = prim['attributes']
    pos = read_accessor(gltf, binary, attrs['POSITION'])
    nrm = read_accessor(gltf, binary, attrs['NORMAL'])
    uv = read_accessor(gltf, binary, attrs['TEXCOORD_0'])
    idx = read_accessor(gltf, binary, prim['indices'])
    if idx.max() > 0xFFFF:
        raise ValueError('정점이 65535 개를 넘음')

    image = gltf['images'][0]
    img = Image.open(io.BytesIO(view_bytes(gltf, binary, image['bufferView']))).convert('RGB')
    src_size = img.size
    img = img.resize((tex_px, tex_px), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=90)

    material = dict(gltf['materials'][prim.get('material', 0)])
    material['name'] = 'ycb_apple'
    material['pbrMetallicRoughness'] = dict(material.get('pbrMetallicRoughness', {}))
    material['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}

    new_pos = normalize(pos)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    write_glb(dst, new_pos, nrm, uv, idx, buf.getvalue(), material)

    ext = pos.max(axis=0) - pos.min(axis=0)
    print(f'원본: 정점 {len(pos)}, 삼각형 {len(idx) // 3}, 크기(m) {np.round(ext, 4).tolist()}, '
          f'텍스처 {src_size[0]}x{src_size[1]}')
    print(f'결과: {dst} ({os.path.getsize(dst) / 1024:.0f} KiB), 텍스처 {tex_px}x{tex_px} JPG, '
          f'범위 {np.round(new_pos.min(axis=0), 3).tolist()} ~ '
          f'{np.round(new_pos.max(axis=0), 3).tolist()}')


if __name__ == '__main__':
    main()
