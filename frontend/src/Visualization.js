import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Default data if none is provided
const defaultData = [
  { name: 'Jan', value: 400 },
  { name: 'Feb', value: 300 },
  { name: 'Mar', value: 200 },
  { name: 'Apr', value: 278 },
  { name: 'May', value: 189 },
];

const Spinner = () => (
  <div role="status" aria-live="polite" style={{ textAlign: 'center', margin: '20px 0' }}>
    <span className="spinner" style={{ display: 'inline-block', width: 32, height: 32, border: '4px solid #ccc', borderTop: '4px solid #8884d8', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></span>
    <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    <div style={{ marginTop: 8, color: '#888' }}>Loading chart...</div>
  </div>
);

function isNumeric(val) {
  return typeof val === 'number' && !isNaN(val) && isFinite(val);
}

const Visualization = ({ chartData = defaultData, loading = false }) => {
  // Edge case: loading
  if (loading) return <Spinner />;

  // Edge case: empty
  if (!Array.isArray(chartData) || chartData.length === 0) {
    return <div aria-live="polite" style={{ color: '#888', marginTop: '10px' }}>No chart data available for this result.</div>;
  }

  // Edge case: malformed or non-numeric
  const hasNonNumeric = chartData.some(d => !('value' in d) || !isNumeric(d.value));
  if (hasNonNumeric) {
    return <div aria-live="polite" style={{ color: '#e63946', marginTop: '10px' }}>Chart data is malformed or contains non-numeric values.</div>;
  }

  // Edge case: only one point
  if (chartData.length === 1) {
    return (
      <div style={{ marginTop: '20px', border: '1px solid #ddd', padding: '10px', borderRadius: '4px' }} aria-label="Data Visualization (single point)">
        <h3>Data Visualization</h3>
        <div style={{ color: '#888', marginBottom: 8 }}>Only one data point available.</div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Edge case: multiple series/unexpected structure
  // (For now, only support single series with 'value' key. If more, show a message.)
  const keys = Object.keys(chartData[0] || {});
  const extraSeries = keys.filter(k => k !== 'name' && k !== 'value');
  if (extraSeries.length > 0) {
    return <div aria-live="polite" style={{ color: '#e67e22', marginTop: '10px' }}>Chart contains multiple series or unexpected structure. Only the 'value' series is shown.</div>;
  }

  // Normal case
  return (
    <div style={{ marginTop: '20px', border: '1px solid #ddd', padding: '10px', borderRadius: '4px' }} aria-label="Data Visualization">
    <h3>Data Visualization</h3>
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#8884d8" />
      </LineChart>
    </ResponsiveContainer>
  </div>
);
};

export default Visualization; 