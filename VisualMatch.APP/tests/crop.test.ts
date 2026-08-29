import assert from 'node:assert/strict'; import test from 'node:test'; import { calculateCropRegion } from '../src/utils/crop';
test('mapeia ROI de preview cover para pixels', () => { const crop = calculateCropRegion({ width: 400, height: 800 }, { width: 1200, height: 1600 }, { x: 50, y: 200, width: 300, height: 400 }); assert.deepEqual(crop, { x: 300, y: 400, width: 600, height: 800 }); });
