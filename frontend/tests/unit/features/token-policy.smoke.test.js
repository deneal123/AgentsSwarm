import fs from 'fs';
import path from 'path';

const roots = [
  path.resolve(__dirname, '../../../src/features/home'),
  path.resolve(__dirname, '../../../src/features/chat'),
];

const RAW_COLOR = /#([0-9a-fA-F]{3,8})|rgba?\(/;

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    const st = fs.statSync(full);
    if (st.isDirectory()) walk(full, acc);
    else if (/\.(js|jsx)$/.test(entry)) acc.push(full);
  }
  return acc;
}

describe('feature token policy smoke', () => {
  it('key home/chat entrypoints avoid raw colors', () => {
    const targetFiles = [
      path.resolve(__dirname, '../../../src/features/home/components/sections/HeroSectionCanonical.jsx'),
      path.resolve(__dirname, '../../../src/features/home/components/sections/BenefitsSectionCanonical.jsx'),
      path.resolve(__dirname, '../../../src/features/chat/page/ChatPageLayout.jsx'),
    ];

    for (const file of targetFiles) {
      const content = fs.readFileSync(file, 'utf8');
      expect(content).not.toMatch(RAW_COLOR);
    }
  });
});
