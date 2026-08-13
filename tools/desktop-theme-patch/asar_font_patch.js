#!/usr/bin/env node

const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

function align4(n) {
  return (n + 3) & ~3;
}

function readAsar(asarPath) {
  const input = fs.readFileSync(asarPath);
  const outerPayload = input.readUInt32LE(0);
  if (outerPayload !== 4) throw new Error(`Unexpected ASAR outer pickle size: ${outerPayload}`);
  const headerPickleSize = input.readUInt32LE(4);
  const headerPayloadSize = input.readUInt32LE(8);
  const jsonLength = input.readUInt32LE(12);
  const json = input.subarray(16, 16 + jsonLength).toString('utf8');
  const header = JSON.parse(json);
  const dataStart = 8 + headerPickleSize;
  if (dataStart !== 12 + headerPayloadSize) throw new Error('Inconsistent ASAR header sizes');
  return { input, header, dataStart };
}

function entryAt(header, archivePath) {
  let node = header;
  for (const part of archivePath.split('/').filter(Boolean)) {
    if (!node.files || !node.files[part]) throw new Error(`Missing ASAR entry: ${archivePath}`);
    node = node.files[part];
  }
  return node;
}

function fileBytes(archive, archivePath) {
  const entry = entryAt(archive.header, archivePath);
  if (entry.unpacked) throw new Error(`Entry is unpacked: ${archivePath}`);
  const offset = Number(entry.offset);
  return archive.input.subarray(archive.dataStart + offset, archive.dataStart + offset + entry.size);
}

function walkFiles(node, prefix = '', output = []) {
  if (!node.files) return output;
  for (const [name, entry] of Object.entries(node.files)) {
    const archivePath = prefix ? `${prefix}/${name}` : name;
    if (entry.files) walkFiles(entry, archivePath, output);
    else if (Object.prototype.hasOwnProperty.call(entry, 'size') && !entry.unpacked) output.push({ archivePath, entry });
  }
  return output;
}

function integrity(bytes, blockSize = 4194304) {
  const blocks = [];
  for (let i = 0; i < bytes.length; i += blockSize) {
    blocks.push(crypto.createHash('sha256').update(bytes.subarray(i, i + blockSize)).digest('hex'));
  }
  return {
    algorithm: 'SHA256',
    hash: crypto.createHash('sha256').update(bytes).digest('hex'),
    blockSize,
    blocks
  };
}

function makeHeaderPickle(header) {
  const json = Buffer.from(JSON.stringify(header), 'utf8');
  const headerPayloadSize = align4(4 + json.length);
  const headerPickleSize = 4 + headerPayloadSize;
  const result = Buffer.alloc(8 + headerPickleSize);
  result.writeUInt32LE(4, 0);
  result.writeUInt32LE(headerPickleSize, 4);
  result.writeUInt32LE(headerPayloadSize, 8);
  result.writeUInt32LE(json.length, 12);
  json.copy(result, 16);
  return result;
}

function main() {
  const [command, asarPath, archivePath, localPath, outputPath] = process.argv.slice(2);
  const archive = readAsar(asarPath);
  if (command === 'header-hash') {
    const jsonLength = archive.input.readUInt32LE(12);
    const hash = crypto.createHash('sha256').update(archive.input.subarray(16, 16 + jsonLength)).digest('hex');
    process.stdout.write(`${hash}\n`);
    return;
  }
  if (command === 'compare') {
    const other = readAsar(archivePath);
    const left = walkFiles(archive.header).map((item) => item.archivePath);
    const right = walkFiles(other.header).map((item) => item.archivePath);
    if (JSON.stringify(left) !== JSON.stringify(right)) throw new Error('Archive file lists differ');
    const changed = left.filter((item) => !fileBytes(archive, item).equals(fileBytes(other, item)));
    process.stdout.write(`${changed.join('\n')}\n`);
    return;
  }
  if (command === 'extract-file') {
    fs.writeFileSync(localPath, fileBytes(archive, archivePath));
    return;
  }
  if (command !== 'replace-file') throw new Error('Use extract-file or replace-file');

  const replacement = fs.readFileSync(localPath);
  const files = walkFiles(archive.header);
  const data = [];
  let offset = 0;
  let found = false;
  for (const item of files) {
    let bytes = fileBytes(archive, item.archivePath);
    if (item.archivePath === archivePath) {
      bytes = replacement;
      found = true;
    }
    item.entry.offset = String(offset);
    item.entry.size = bytes.length;
    if (item.entry.integrity) item.entry.integrity = integrity(bytes, item.entry.integrity.blockSize || 4194304);
    data.push(bytes);
    offset += bytes.length;
  }
  if (!found) throw new Error(`Replacement target not found: ${archivePath}`);
  const packed = Buffer.concat([makeHeaderPickle(archive.header), ...data]);
  fs.writeFileSync(outputPath, packed);

  const verify = readAsar(outputPath);
  const actual = fileBytes(verify, archivePath);
  if (!actual.equals(replacement)) throw new Error('Repacked ASAR verification failed');
}

main();
