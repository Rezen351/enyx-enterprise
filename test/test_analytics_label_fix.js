// Targeted verification for Analytics.jsx displayName logic
// Run with: node test_analytics_label_fix.js

function simulateDisplayName(metric, tags) {
  const tagByKey = {};
  for (const t of tags) {
    if (t.tag_name) tagByKey[t.tag_name] = t;
    if (t.source_key && t.source_key !== t.tag_name) tagByKey[t.source_key] = t;
  }
  const t = tagByKey[metric];
  if (t) {
    const displayStr = (t.display_name || '').trim();
    if (displayStr) return displayStr;
    const labelStr = (t.label || '').trim();
    if (labelStr) return labelStr;
    const tagNameStr = (t.tag_name || '').trim();
    if (tagNameStr) return tagNameStr;
  }
  const actuatorPrefix = 'telemetry.outputs.';
  if (metric.startsWith(actuatorPrefix)) {
    const outputName = metric.slice(actuatorPrefix.length);
    const actuatorTag = tags.find((at) => at.kind === 'actuator' && (at.tag_name === outputName || at.source_key === outputName));
    if (actuatorTag) {
      const displayStr = (actuatorTag.display_name || '').trim();
      if (displayStr) return displayStr;
      const labelStr = (actuatorTag.label || '').trim();
      if (labelStr) return labelStr;
      const tagNameStr = (actuatorTag.tag_name || '').trim();
      if (tagNameStr) return tagNameStr;
    }
  }
  return metric;
}

const tags = [
  { kind: 'sensor', tag_name: 'temp', source_key: 'sensor.temp', display_name: '', label: '' },
  { kind: 'actuator', tag_name: 'alarm', source_key: 'buzzer', display_name: 'Alarm', label: '' },
  { kind: 'sensor', tag_name: 'sensor.temp', source_key: 'sensor.temp', display_name: '', label: 'Temperature' },
  { kind: 'actuator', tag_name: 'pump', source_key: 'pump', display_name: 'Water Pump', label: '' },
];

const cases = [
  { metric: 'temp', expected: 'temp', desc: 'sensor tag_name exact match without display_name/label -> tag_name' },
  { metric: 'telemetry.outputs.buzzer', expected: 'Alarm', desc: 'actuator fallback via prefix with display_name -> display_name' },
  { metric: 'telemetry.outputs.pump', expected: 'Water Pump', desc: 'actuator fallback via prefix with display_name -> display_name' },
  { metric: 'sensor.temp', expected: 'Temperature', desc: 'sensor tag fallback via tagByKey with label -> label' },
  { metric: 'unknown.metric', expected: 'unknown.metric', desc: 'unknown metric -> raw key' },
];

let passed = 0;
let failed = 0;

for (const c of cases) {
  const result = simulateDisplayName(c.metric, tags);
  const ok = result === c.expected;
  if (ok) passed++;
  else failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}: ${c.desc}`);
  if (!ok) console.log(`  metric: ${c.metric}`);
  console.log(`  expected: ${c.expected}`);
  console.log(`  got:      ${result}`);
}

console.log(`\nResults: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
