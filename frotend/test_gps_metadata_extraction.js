/**
 * AUTOMATED TEST SUITE: Field Health Automatic GPS Metadata Extraction
 * Validates:
 * 1. DOM elements and dynamic GPS cards structure in index.html
 * 2. Required exact labels ("GPS Location Detected", "Latitude", "Longitude", "GPS Source: Photo Metadata", "Location Extraction Status: Successful", "GPS Location Not Found")
 * 3. Loading state and fallback to manual coordinates
 * 4. Binary EXIF GPS parsing with synthetic GPS JPEG and non-GPS JPEG
 * 5. Dynamic field population and UI controller integration in fieldHealth.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let passed = 0;
let failed = 0;

function assert(condition, testName, detail = '') {
  if (condition) {
    passed++;
    console.log(`  [PASS] ${testName}`);
  } else {
    failed++;
    console.error(`  [FAIL] ${testName}: ${detail}`);
  }
}

console.log('====================================================================');
console.log(' FIELD HEALTH: GPS METADATA EXTRACTION VERIFICATION SUITE');
console.log('====================================================================\n');

// -------------------------------------------------------------------------
// 1. Structure Audit of index.html
// -------------------------------------------------------------------------
console.log('--- TEST SECTION 1: index.html DOM Structure & UI Cards ---');

const indexHtmlPath = path.join(__dirname, 'index.html');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');

assert(indexHtml.includes('id="field-gps-container"'), 'Dynamic GPS container #field-gps-container exists');
assert(indexHtml.includes('id="gps-box-default"'), 'Default notice #gps-box-default exists');
assert(indexHtml.includes('id="gps-box-loading"'), 'Loading indicator #gps-box-loading exists');
assert(indexHtml.includes('id="gps-box-success"'), 'Success card #gps-box-success exists');
assert(indexHtml.includes('id="gps-box-unavailable"'), 'Unavailable card #gps-box-unavailable exists');
assert(indexHtml.includes('id="gps-detected-lat"'), 'Latitude target #gps-detected-lat exists');
assert(indexHtml.includes('id="gps-detected-lon"'), 'Longitude target #gps-detected-lon exists');

// Exact label checks from requirements
assert(indexHtml.includes('GPS Location Detected'), 'Displays "GPS Location Detected" headline in success card');
assert(indexHtml.includes('GPS Source:') && indexHtml.includes('Photo Metadata'), 'Displays "GPS Source: Photo Metadata"');
assert(indexHtml.includes('Location Extraction Status:') && indexHtml.includes('Successful'), 'Displays "Location Extraction Status: Successful"');
assert(indexHtml.includes('GPS Location Not Found'), 'Displays "GPS Location Not Found" in unavailable card');
assert(indexHtml.includes('Extracting GPS Metadata...'), 'Displays loading text in loading card');
assert(indexHtml.includes('GPS extraction will be available after integration.'), 'Preserves default notice text for backward compatibility');

// -------------------------------------------------------------------------
// 2. Controller Audit of fieldHealth.js
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 2: fieldHealth.js Logic & Engine Audit ---');

const fieldHealthPath = path.join(__dirname, 'src', 'fieldHealth.js');
const fieldHealthJs = fs.readFileSync(fieldHealthPath, 'utf-8');

assert(fieldHealthJs.includes('gpsBoxDefault') && fieldHealthJs.includes('gpsBoxSuccess'), 'References GPS DOM elements');
assert(fieldHealthJs.includes('setGpsStatus'), 'Implements setGpsStatus state switcher');
assert(fieldHealthJs.includes('extractGpsFromBuffer'), 'Implements native extractGpsFromBuffer binary parser');
assert(fieldHealthJs.includes('parseTiffGps'), 'Implements parseTiffGps TIFF header & IFD parser');
assert(fieldHealthJs.includes('readRationals'), 'Implements readRationals TIFF rational reader');
assert(fieldHealthJs.includes('extractGpsMetadata'), 'Implements multi-tiered extractGpsMetadata');
assert(fieldHealthJs.includes('inputLatitude.value = gpsData.latitude.toFixed(6)'), 'Populates inputLatitude automatically');
assert(fieldHealthJs.includes('inputLongitude.value = gpsData.longitude.toFixed(6)'), 'Populates inputLongitude automatically');
assert(fieldHealthJs.includes('setGpsStatus(\'loading\')'), 'Activates loading state during metadata scan');
assert(fieldHealthJs.includes('setGpsStatus(\'default\')'), 'Resets to default state on image removal and form reset');

// -------------------------------------------------------------------------
// 3. Functional Binary Parser Verification with Synthetic EXIF
// -------------------------------------------------------------------------
console.log('\n--- TEST SECTION 3: Functional Binary EXIF Parser Unit Tests ---');

// Build a synthetic minimal JPEG with valid EXIF GPS markers
function createSyntheticGpsJpeg(latDeg, lonDeg) {
  // Little-endian TIFF structure
  const tiffHeader = Buffer.from([
    0x49, 0x49,             // Byte order: II (little-endian)
    0x2A, 0x00,             // 42
    0x08, 0x00, 0x00, 0x00  // IFD0 offset = 8
  ]);

  // IFD0: 1 entry (GPSInfo tag 0x8825), then next IFD offset 0
  const gpsIfdOffset = 8 + 2 + 12 + 4; // 26
  const ifd0 = Buffer.alloc(2 + 12 + 4);
  ifd0.writeUInt16LE(1, 0); // 1 entry
  ifd0.writeUInt16LE(0x8825, 2); // tag GPSInfo
  ifd0.writeUInt16LE(4, 4); // type LONG
  ifd0.writeUInt32LE(1, 6); // count 1
  ifd0.writeUInt32LE(gpsIfdOffset, 10); // offset to GPS IFD
  ifd0.writeUInt32LE(0, 14); // next IFD offset

  // GPS IFD: 4 entries (LatRef, Lat, LonRef, Lon)
  // Tags:
  // 0x0001: GPSLatitudeRef (ASCII, count 2, 'N\0')
  // 0x0002: GPSLatitude (RATIONAL, count 3, offset to values)
  // 0x0003: GPSLongitudeRef (ASCII, count 2, 'E\0')
  // 0x0004: GPSLongitude (RATIONAL, count 3, offset to values)
  const gpsValuesOffset = gpsIfdOffset + 2 + 4 * 12 + 4; // 26 + 2 + 48 + 4 = 80
  const gpsIfd = Buffer.alloc(2 + 4 * 12 + 4);
  gpsIfd.writeUInt16LE(4, 0); // 4 entries

  // 1. LatRef
  gpsIfd.writeUInt16LE(0x0001, 2);
  gpsIfd.writeUInt16LE(2, 4); // ASCII
  gpsIfd.writeUInt32LE(2, 6); // count 2
  gpsIfd.write('N\0', 10); // inline

  // 2. Lat
  gpsIfd.writeUInt16LE(0x0002, 14);
  gpsIfd.writeUInt16LE(5, 16); // RATIONAL
  gpsIfd.writeUInt32LE(3, 18); // count 3
  gpsIfd.writeUInt32LE(gpsValuesOffset, 22);

  // 3. LonRef
  gpsIfd.writeUInt16LE(0x0003, 26);
  gpsIfd.writeUInt16LE(2, 28); // ASCII
  gpsIfd.writeUInt32LE(2, 30); // count 2
  gpsIfd.write('E\0', 34); // inline

  // 4. Lon
  gpsIfd.writeUInt16LE(0x0004, 38);
  gpsIfd.writeUInt16LE(5, 40); // RATIONAL
  gpsIfd.writeUInt32LE(3, 42); // count 3
  gpsIfd.writeUInt32LE(gpsValuesOffset + 24, 46);

  gpsIfd.writeUInt32LE(0, 50); // next IFD 0

  // Rationals: 3 pairs for Lat (deg/1, min/1, sec/10000), 3 pairs for Lon
  const rationals = Buffer.alloc(48);
  const latInt = Math.floor(latDeg);
  const latMin = Math.floor((latDeg - latInt) * 60);
  const latSec = Math.round(((latDeg - latInt) * 60 - latMin) * 60 * 10000);

  rationals.writeUInt32LE(latInt, 0);
  rationals.writeUInt32LE(1, 4);
  rationals.writeUInt32LE(latMin, 8);
  rationals.writeUInt32LE(1, 12);
  rationals.writeUInt32LE(latSec, 16);
  rationals.writeUInt32LE(10000, 20);

  const lonInt = Math.floor(lonDeg);
  const lonMin = Math.floor((lonDeg - lonInt) * 60);
  const lonSec = Math.round(((lonDeg - lonInt) * 60 - lonMin) * 60 * 10000);

  rationals.writeUInt32LE(lonInt, 24);
  rationals.writeUInt32LE(1, 28);
  rationals.writeUInt32LE(lonMin, 32);
  rationals.writeUInt32LE(1, 36);
  rationals.writeUInt32LE(lonSec, 40);
  rationals.writeUInt32LE(10000, 44);

  const exifPayload = Buffer.concat([tiffHeader, ifd0, gpsIfd, rationals]);
  const app1Header = Buffer.from([
    0xFF, 0xE1, // APP1 marker
    0x00, 0x00, // length placeholder
    0x45, 0x78, 0x69, 0x66, 0x00, 0x00 // 'Exif\0\0'
  ]);
  app1Header.writeUInt16BE(exifPayload.length + 8, 2);

  const jpegSOI = Buffer.from([0xFF, 0xD8]);
  const jpegEOI = Buffer.from([0xFF, 0xD9]);

  return Buffer.concat([jpegSOI, app1Header, exifPayload, jpegEOI]);
}

// Test parsing with synthetic JPEG
const testLat = 13.433905;
const testLon = 79.578698;
const synthJpeg = createSyntheticGpsJpeg(testLat, testLon);

// Evaluate parser function from fieldHealth.js source
const parseTiffMatch = fieldHealthJs.match(/const parseTiffGps = ([\s\S]*?\n  \};)/);
const readRatMatch = fieldHealthJs.match(/const readRationals = ([\s\S]*?\n  \};)/);
const extractGpsMatch = fieldHealthJs.match(/const extractGpsFromBuffer = ([\s\S]*?\n  \};)/);

assert(Boolean(parseTiffMatch && readRatMatch && extractGpsMatch), 'Found all parser functions in fieldHealth.js');

const parserScript = `
  ${readRatMatch[0]}
  ${parseTiffMatch[0]}
  ${extractGpsMatch[0]}
  const res = extractGpsFromBuffer(synthJpeg.buffer.slice(synthJpeg.byteOffset, synthJpeg.byteOffset + synthJpeg.byteLength));
  res;
`;

const parsedGps = eval(`
  (function(synthJpeg) {
    ${readRatMatch[0]}
    ${parseTiffMatch[0]}
    ${extractGpsMatch[0]}
    return extractGpsFromBuffer(synthJpeg.buffer.slice(synthJpeg.byteOffset, synthJpeg.byteOffset + synthJpeg.byteLength));
  })(synthJpeg)
`);

assert(Boolean(parsedGps), 'Parser successfully extracts GPS from valid image buffer');
assert(Math.abs(parsedGps.latitude - testLat) < 0.0001, `Extracted latitude is accurate (${parsedGps.latitude} ≈ ${testLat})`);
assert(Math.abs(parsedGps.longitude - testLon) < 0.0001, `Extracted longitude is accurate (${parsedGps.longitude} ≈ ${testLon})`);
assert(parsedGps.latitudeRef === 'N', 'Extracted latitudeRef is "N"');
assert(parsedGps.longitudeRef === 'E', 'Extracted longitudeRef is "E"');

// Test with non-GPS image buffer
const blankJpeg = Buffer.from([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9]);
const blankGps = eval(`
  (function(blankJpeg) {
    ${readRatMatch[0]}
    ${parseTiffMatch[0]}
    ${extractGpsMatch[0]}
    return extractGpsFromBuffer(blankJpeg.buffer.slice(blankJpeg.byteOffset, blankJpeg.byteOffset + blankJpeg.byteLength));
  })(blankJpeg)
`);

assert(blankGps === null, 'Parser returns null when image has no GPS EXIF (graceful fallback)');

console.log('\n====================================================================');
console.log(` RESULTS: ${passed} PASSED, ${failed} FAILED`);
console.log('====================================================================');

if (failed > 0) process.exit(1);
