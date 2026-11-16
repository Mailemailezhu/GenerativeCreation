"""从 app/core/hints.py 的 DEFAULT 生成 config/hints.xml（改完默认文案时跑一次）。"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'app'))

from core import hints, paths

HEAD = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<!-- 界面上的所有提示文案都在这个文件里。改完保存，重开 GC 生效。',
      '     缺项会自动回落到程序内置的默认值；tools / views 的顺序就是界面上的顺序。-->',
]


def body():
    d = hints.DEFAULT
    out = ['<gc-hints>']
    out.append('  <tips>')
    for k, v in d['tips'].items():
        out.append('    <tip key="%s">%s</tip>' % (k, escape(v)))
    out.append('  </tips>')
    out.append('  <ui>')
    for k, v in d['ui'].items():
        out.append('    <item key="%s">%s</item>' % (k, escape(v)))
    out.append('  </ui>')
    out.append('  <tools>')
    for k, name, tip in d['tools']:
        out.append('    <tool key="%s" name="%s">%s</tool>' % (k, escape(name), escape(tip)))
    out.append('  </tools>')
    out.append('  <views>')
    for k, label, tip in d['views']:
        out.append('    <view key="%s" label="%s">%s</view>' % (k, escape(label), escape(tip)))
    out.append('  </views>')
    out.append('</gc-hints>')
    return out


def main():
    p = Path(paths.root()) / 'config' / 'hints.xml'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(HEAD + body()) + '\n', encoding='utf-8')
    print('WROTE %s %d bytes' % (p, p.stat().st_size))


if __name__ == '__main__':
    main()