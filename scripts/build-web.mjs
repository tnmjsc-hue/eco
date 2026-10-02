import { copyFile, mkdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

await mkdir('public/vendor', { recursive: true });
for (const [from, to] of [
  ['node_modules/echarts/dist/echarts.min.js', 'echarts.min.js'],
  ['node_modules/echarts/LICENSE', 'echarts-LICENSE.txt'],
  ['node_modules/echarts/NOTICE', 'echarts-NOTICE.txt'],
  ['node_modules/lucide/dist/umd/lucide.min.js', 'lucide.min.js'],
  ['node_modules/lucide/LICENSE', 'lucide-LICENSE.txt'],
]) await copyFile(from, `public/vendor/${to}`);
for (const name of ['echarts.min.js', 'lucide.min.js']) {
  const buffer = await readFile(`public/vendor/${name}`);
  console.log(`${name}: ${buffer.length} bytes, sha256=${createHash('sha256').update(buffer).digest('hex')}`);
}
