// ============================================================================
// gen_manifest.mjs — regenerate manifest.generated.mjs from index.html
// ============================================================================
//
// AXIOMS:
//   A1: The GUI's element inventory is exactly the set of id="" attributes
//       in uiassets/index.html (authoritative source of truth).
//   A2: A test comment must exist for EVERY element, even decorative ones
//       (decorative = "inspect" action: assert presence, no interaction).
//   A3: Inline on* handlers in index.html are the most reliable indicator of
//       which routine an element triggers.
//
// THEOREMS:
//   T1: Running this generator after any index.html change keeps the
//       self-test coverage manifest in sync (no silently untested element).
//
// APPLICATIONS:
//   Writes manifest.generated.mjs: one commented entry per id.
//
// CITATIONS:
//   - HTML Living Standard, id attribute: https://html.spec.whatwg.org/multipage/dom.html#the-id-attribute
//
// TIMING: O(N) parse of index.html (~1511 lines) — <10ms.
// ============================================================================
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const INDEX = join(HERE, '..', 'index.html');
const OUT = join(HERE, 'manifest.generated.mjs');

const html = readFileSync(INDEX, 'utf8');

// ── Parse: stack-based scan so each id knows its nearest ancestor id ──────
const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g;
const stack = []; // {tag, id}
const elements = [];
let m;
while ((m = tagRe.exec(html)) !== null) {
  const [, close, tag, attrs, selfClose] = m;
  const idMatch = attrs.match(/\sid="([^"]+)"/);
  const id = idMatch ? idMatch[1] : null;
  if (close) {
    // pop until matching tag (tolerant of implied closes)
    for (let i = stack.length - 1; i >= 0; i--) {
      if (stack[i].tag === tag) { stack.length = i; break; }
    }
    continue;
  }
  if (id) {
    const typeMatch = attrs.match(/\stype="([^"]+)"/);
    const handlerMatch = attrs.match(/\son(click|change|input|submit|load|keyup|keydown)="([^"]+)"/);
    // nearest ancestor that has an id = owning group; fall back to a
    // structural class (sidebar/header/footer) so structural controls are
    // grouped meaningfully instead of dumping into (root).
    const owner = [...stack].reverse().find(
      (s) => s.id || (s.cls && ['sidebar', 'header', 'footer', 'nav'].some((c) => s.cls.includes(c))),
    );
    elements.push({
      id,
      tag: tag.toLowerCase(),
      type: typeMatch ? typeMatch[1].toLowerCase() : '',
      inline: handlerMatch ? `${handlerMatch[1]}: ${handlerMatch[2]}` : '',
      group: owner ? (owner.id || `.${owner.cls.split(/\s+/)[0]}`) : '(root)',
      selfClose: Boolean(selfClose),
    });
  }
  if (!selfClose && !['meta', 'link', 'br', 'hr', 'img', 'input', 'source', 'area', 'col'].includes(tag.toLowerCase())) {
    const clsMatch = attrs.match(/\sclass="([^"]+)"/);
    stack.push({ tag: tag.toLowerCase(), id, cls: clsMatch ? clsMatch[1] : '' });
  }
}

// ── Decide the TEST action per element ────────────────────────────────────
function actionFor(el) {
  const { tag, type, id } = el;
  if (tag === 'button') return 'click';
  if (tag === 'select') return 'change';
  if (tag === 'textarea') return 'type';
  if (tag === 'input') {
    if (type === 'checkbox' || type === 'radio' || type === 'submit' || type === 'button') return 'click';
    if (type === 'range') return 'input';
    if (type === 'file') return 'event';      // cannot set files headlessly; dispatch change
    return 'type';                             // text, number, email, password, search, date...
  }
  if (tag === 'video') return 'inspect';
  if (el.inline) return 'click';
  // Decorative / structural nodes: assert presence only.
  return 'inspect';
}

const lines = [];
lines.push('// ============================================================================');
lines.push('// manifest.generated.mjs — AUTO-GENERATED coverage manifest (index.html ids)  ');
lines.push('// ============================================================================');
lines.push('// Every element of the Baloon Shield Maker GUI with the TEST that exercises it.');
lines.push('// Regenerate after editing index.html:  node gen_manifest.mjs');
lines.push(`// Source: index.html (${elements.length} unique ids parsed)`);
lines.push('// ============================================================================');
lines.push('');
lines.push('export const ELEMENTS = [');

let lastGroup = null;
for (const el of elements) {
  if (el.group !== lastGroup) {
    lines.push('');
    lines.push(`  // ── group: ${el.group} ──`);
    lastGroup = el.group;
  }
  const act = actionFor(el);
  const why = {
    click: 'TEST: click → must not throw',
    change: 'TEST: select new option → dispatch change → no throw',
    type: 'TEST: set value → dispatch input+change → no throw',
    input: 'TEST: set slider value → dispatch input+change → no throw',
    event: 'TEST: dispatch change (no real file) → no throw',
    inspect: 'TEST: exists in DOM (decorative/static node)',
  }[act];
  const inlineNote = el.inline ? ` ; inline handler: ${el.inline}` : '';
  lines.push(`  // #${el.id} <${el.tag}${el.type ? ' type=' + el.type : ''}> — ${why}${inlineNote}`);
  lines.push(`  { id: ${JSON.stringify(el.id)}, tag: ${JSON.stringify(el.tag)}, type: ${JSON.stringify(el.type)}, action: ${JSON.stringify(act)}, group: ${JSON.stringify(el.group)} },`);
}
lines.push('];');
lines.push('');
writeFileSync(OUT, lines.join('\n'), 'utf8');
console.log(`manifest.generated.mjs written: ${elements.length} elements, ${new Set(elements.map(e => e.group)).size} groups`);
