/* Read values from an operator's XLSX locally; no macros, formulas or external links execute. */
import './vendor/jszip-3.10.1.min.js';

const MiB = 1024 * 1024;
const limits = { archive: 5 * MiB, part: 12 * MiB, total: 32 * MiB, files: 512, rows: 15000, columns: 256, cells: 200000 };
const indexByName = (node, name) => Array.from(node?.children ?? []).filter(child => child.localName === name);
const first = (node, name) => Array.from(node?.children ?? []).find(child => child.localName === name);
const sizeError = () => new Error('This workbook is too large to preview. Export one location and the needed weeks, or use CSV.');

function resolvePart(source, target) {
  if (!target || /[?#\\]/.test(target) || /^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith('//')) {
    throw new Error('The workbook contains an unsupported part reference.');
  }
  const parts = target.startsWith('/') ? [] : source.split('/').slice(0, -1);
  for (const segment of target.split('/')) {
    if (segment === '..') {
      if (!parts.length) throw new Error('Invalid workbook part path.');
      parts.pop();
    } else if (segment && segment !== '.') parts.push(segment);
  }
  return parts.join('/');
}

function relationshipsPath(part) {
  const slash = part.lastIndexOf('/') + 1;
  return part.slice(0, slash) + '_rels/' + part.slice(slash) + '.rels';
}

/* Per-part streaming cap is independent of the size declared by the ZIP. */
async function readXml(zip, path) {
  const member = zip.file(path);
  if (!member) throw new Error('A required worksheet part is missing. Re-export as XLSX or CSV.');
  const xml = await new Promise((resolve, reject) => {
    const stream = member.internalStream('uint8array');
    let decoder;
    const parts = [];
    let bytes = 0;
    stream.on('data', chunk => {
      bytes += chunk.length;
      if (bytes > limits.part) {
        stream.pause();
        reject(sizeError());
        return;
      }
      try {
        if (!decoder) {
          let encoding = 'utf-8';
          if (chunk[0] === 0xff && chunk[1] === 0xfe || chunk[0] === 0x3c && chunk[1] === 0) encoding = 'utf-16le';
          if (chunk[0] === 0xfe && chunk[1] === 0xff || chunk[0] === 0 && chunk[1] === 0x3c) encoding = 'utf-16be';
          decoder = new TextDecoder(encoding, { fatal: true });
        }
        parts.push(decoder.decode(chunk, { stream: true }));
      }
      catch (error) { stream.pause(); reject(error); }
    });
    stream.on('error', reject);
    stream.on('end', () => {
      try { if (decoder) parts.push(decoder.decode()); resolve(parts.join('')); }
      catch (error) { reject(error); }
    });
    stream.resume();
  });
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error('Unsupported XML declarations in the workbook.');
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  if (doc.getElementsByTagNameNS('*', 'parsererror').length) throw new Error('A workbook part is not valid XML.');
  return doc.documentElement;
}

async function relationships(zip, source) {
  const root = await readXml(zip, relationshipsPath(source));
  const result = new Map();
  for (const rel of indexByName(root, 'Relationship')) {
    if (rel.getAttribute('TargetMode') === 'External') continue;
    const id = rel.getAttribute('Id');
    if (result.has(id)) throw new Error('Duplicate workbook relationship.');
    result.set(id, { type: rel.getAttribute('Type')?.split('/').pop(), path: resolvePart(source, rel.getAttribute('Target')) });
  }
  return result;
}

function textRuns(container) {
  // Rich text has several runs; phonetic annotations are metadata, not part of the value.
  return Array.from(container?.children ?? []).map(child => {
    if (child.localName === 't') return child.textContent;
    if (child.localName === 'r') return first(child, 't')?.textContent ?? '';
    return '';
  }).join('');
}

function cellValue(cell, strings) {
  const type = cell.getAttribute('t') || 'n';
  if (type === 'inlineStr') return textRuns(first(cell, 'is'));
  const value = first(cell, 'v')?.textContent;
  if (value == null || value === '') return '';
  switch (type) {
    case 's': {
      const index = Number(value);
      if (!/^\d+$/.test(value) || index >= strings.length) throw new Error('Invalid shared-string index.');
      return strings[index];
    }
    case 'n': {
      const number = Number(value);
      if (!Number.isFinite(number)) throw new Error('A worksheet contains an invalid number.');
      return number;
    }
    case 'b':
      if (value !== '0' && value !== '1') throw new Error('Invalid spreadsheet boolean.');
      return value === '1';
    case 'str': case 'd': case 'e': return value;
    default: throw new Error('A worksheet uses an unsupported cell value type.');
  }
}

function columnIndex(reference, rowNumber) {
  const match = /^([A-Z]{1,3})([1-9]\d*)$/.exec(reference);
  if (!match || Number(match[2]) !== rowNumber) throw new Error('Invalid worksheet cell address.');
  let column = 0;
  for (const letter of match[1]) column = column * 26 + letter.charCodeAt(0) - 64;
  return column - 1;
}

function parseRows(sheet, strings) {
  const sheetData = first(sheet, 'sheetData');
  if (!sheetData) throw new Error('The selected sheet contains no worksheet data.');
  const result = [];
  let cellCount = 0;
  for (const row of indexByName(sheetData, 'row')) {
    const rowNumber = row.hasAttribute('r') ? Number(row.getAttribute('r')) : result.length + 1;
    if (!Number.isInteger(rowNumber) || rowNumber <= result.length) throw new Error('Worksheet rows are duplicated or out of order.');
    if (rowNumber > limits.rows) throw sizeError();
    while (result.length < rowNumber - 1) result.push([]);
    const values = [];
    for (const cell of indexByName(row, 'c')) {
      const column = cell.hasAttribute('r') ? columnIndex(cell.getAttribute('r'), rowNumber) : values.length;
      if (column < values.length) throw new Error('Worksheet cells are duplicated or out of order.');
      if (column >= limits.columns || ++cellCount > limits.cells) throw sizeError();
      while (values.length < column) values.push('');
      values.push(cellValue(cell, strings));
    }
    result.push(values);
  }
  return result;
}

export async function readXlsx(file) {
  if (!file?.size || file.size > limits.archive) throw sizeError();
  const zip = await globalThis.JSZip.loadAsync(await file.arrayBuffer());
  const entries = Object.values(zip.files);
  if (entries.length > limits.files) throw sizeError();
  /* JSZip 3.10.1's compressed input exposes the central-directory uncompressed size. */
  const declaredBytes = entries.reduce((sum, entry) => sum + (entry.dir ? 0 : entry._data.uncompressedSize), 0);
  if (!Number.isSafeInteger(declaredBytes) || declaredBytes > limits.total) throw sizeError();

  const packageRels = await relationships(zip, '');
  const workbookPath = [...packageRels.values()].find(rel => rel.type === 'officeDocument')?.path;
  if (!workbookPath) throw new Error('Choose an XLSX workbook or a CSV export.');
  const workbook = await readXml(zip, workbookPath);
  const relations = await relationships(zip, workbookPath);
  const sheets = new Map();
  for (const sheet of indexByName(first(workbook, 'sheets'), 'sheet')) {
    const id = Array.from(sheet.attributes).find(attr => attr.localName === 'id' && attr.namespaceURI)?.value;
    const rel = relations.get(id);
    if (rel?.type !== 'worksheet') continue;
    const name = sheet.getAttribute('name');
    if (!name || sheets.has(name)) throw new Error('A worksheet name is missing or duplicated.');
    sheets.set(name, rel.path);
  }
  if (!sheets.size) throw new Error('The workbook contains no readable worksheets.');
  const stringPart = [...relations.values()].find(rel => rel.type === 'sharedStrings');
  const strings = stringPart ? indexByName(await readXml(zip, stringPart.path), 'si').map(textRuns) : [];
  const date1904 = ['1', 'true'].includes(first(workbook, 'workbookPr')?.getAttribute('date1904'));
  return {
    names: [...sheets.keys()],
    date1904,
    async rows(name) {
      if (!sheets.has(name)) throw new Error('Select a worksheet from this workbook.');
      return parseRows(await readXml(zip, sheets.get(name)), strings);
    }
  };
}
