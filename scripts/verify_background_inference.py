"""Inference RMBG that qua HTTP tren ca dataset duoc thay nen xam de test."""
import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen
import cv2
import numpy as np
from fish_features.preprocessing import segment


def main():
    folder = Path('outputs/background-check')
    folder.mkdir(parents=True, exist_ok=True)
    source = sorted(Path('data/images').glob('*.png'))[0]
    image = cv2.imread(str(source))
    mask, _, _, _, _ = segment(image, 245)
    gray_background = image.copy()
    gray_background[mask == 0] = [165, 180, 170]
    cv2.imencode('.png', gray_background)[1].tofile(str(folder/'gray-background.png'))
    before_mask, _, _, before_warnings, _ = segment(gray_background, 245)
    request = Request('http://127.0.0.1:8000/api/search?filename=gray-background.png&background=rmbg2',
        data=cv2.imencode('.png', gray_background)[1].tobytes(), method='POST',
        headers={'Content-Type':'application/octet-stream'})
    with urlopen(request, timeout=300) as response:
        result = json.load(response)
    assert result['preparation']['background_removal']['applied']
    assert result['preparation']['background_removal']['model_id'] == 'briaai/RMBG-2.0'
    assert len(result['results']) == 5
    assert .02 < result['query']['metadata']['occupancy'] < .8
    assert 'unusual_occupancy' not in result['query']['metadata']['warnings']
    for kind, data in result['previews'].items():
        (folder / f'{kind}.png').write_bytes(base64.b64decode(data.split(',', 1)[1]))
    (folder/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'source':source.name, 'input':'dataset fish composited on gray-green background for controlled test',
        'before_occupancy':float(before_mask.mean()), 'before_warnings':before_warnings,
        'after_occupancy':result['query']['metadata']['occupancy'], 'after_warnings':result['query']['metadata']['warnings'],
        'top5_count':len(result['results']), 'background_removal':result['preparation']['background_removal']}
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('PASS: real pretrained RMBG inference, white background, valid feature mask and top5 through web API')


if __name__ == '__main__':
    main()
