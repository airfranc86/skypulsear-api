#!/usr/bin/env node
/**
 * Valida contrato de la API SkyPulse frente al dashboard.
 * Uso: API_BASE_URL=https://... API_KEY=... node scripts/validate-api-contract.mjs
 */

const BASE = process.env.API_BASE_URL || 'https://skypulsear-api.onrender.com';
const API_KEY = process.env.API_KEY || 'demo-key';

const headers = { 'X-API-Key': API_KEY };

function log(ok, msg) {
  console.log(ok ? 'OK' : 'FAIL', msg);
}

async function checkCurrent() {
  console.log('\n--- GET /api/v1/weather/current ---');
  const r = await fetch(`${BASE}/api/v1/weather/current?lat=-34.6&lon=-58.4`, { headers });
  if (!r.ok) {
    log(false, `status ${r.status}`);
    return;
  }
  const data = await r.json();
  const c = data.current || {};
  log(typeof c.temperature === 'number', 'current.temperature number');
  log(typeof c.humidity === 'number', 'current.humidity number');
  log(typeof c.wind_speed === 'number', 'current.wind_speed number');
  log(c.wind_speed >= 0 && c.wind_speed <= 50, 'current.wind_speed plausible (0-50 m/s)');
  log(typeof c.wind_direction === 'string', 'current.wind_direction string');
  log(typeof c.pressure === 'number', 'current.pressure number');
  if (c.wind_direction_deg != null) {
    log(c.wind_direction_deg >= 0 && c.wind_direction_deg <= 360, 'current.wind_direction_deg 0-360');
  }
  if (c.precipitation != null) log(typeof c.precipitation === 'number', 'current.precipitation number');
  if (c.cloud_cover != null) log(typeof c.cloud_cover === 'number', 'current.cloud_cover number');
}

async function checkForecast() {
  console.log('\n--- GET /api/v1/weather/forecast ---');
  const r = await fetch(`${BASE}/api/v1/weather/forecast?lat=-34.6&lon=-58.4&hours=24`, { headers });
  if (!r.ok) {
    log(false, `status ${r.status}`);
    return;
  }
  const data = await r.json();
  const arr = data.forecast || [];
  log(Array.isArray(arr), 'forecast array');
  if (arr.length > 0) {
    const f = arr[0];
    log(typeof f.temperature === 'number', 'forecast[0].temperature number');
    log(typeof f.wind_speed === 'number', 'forecast[0].wind_speed number');
    log(typeof f.precipitation === 'number', 'forecast[0].precipitation number');
  }
}

async function checkRiskScore() {
  console.log('\n--- POST /api/v1/risk-score ---');
  const r = await fetch(`${BASE}/api/v1/risk-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify({ lat: -34.6, lon: -58.4, profile: 'piloto', hours_ahead: 6 }),
  });
  if (!r.ok) {
    log(false, `status ${r.status}`);
    return;
  }
  const data = await r.json();
  const inRange05 = (v) => typeof v === 'number' && v >= 0 && v <= 5;
  log(inRange05(data.score), 'score in [0,5]');
  const subScores = ['temperature_risk', 'wind_risk', 'precipitation_risk', 'storm_risk', 'hail_risk', 'pattern_risk', 'alert_risk'];
  for (const k of subScores) {
    if (data[k] !== undefined) log(inRange05(data[k]), `${k} in [0,5]`);
  }
}

(async () => {
  await checkCurrent();
  await checkForecast();
  await checkRiskScore();
  console.log('\nDone.');
})();
