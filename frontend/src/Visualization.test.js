import React from 'react';
import { render, screen } from '@testing-library/react';
import Visualization from './Visualization';

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe('Visualization component', () => {
  it('shows message for empty chartData', () => {
    render(<Visualization chartData={[]} />);
    expect(screen.getByText(/No chart data available/i)).toBeInTheDocument();
  });

  it('shows chart and note for single-point chartData', () => {
    render(<Visualization chartData={[{ name: 'A', value: 42 }]} />);
    expect(screen.getByText(/Only one data point available/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Data Visualization \(single point\)/i)).toBeInTheDocument();
  });

  it('shows error for non-numeric/malformed chartData', () => {
    render(<Visualization chartData={[{ name: 'A', value: 'not-a-number' }]} />);
    expect(screen.getByText(/malformed or contains non-numeric/i)).toBeInTheDocument();
  });

  it('shows warning for extra series', () => {
    render(<Visualization chartData={[
      { name: 'A', value: 1, extra: 2 },
      { name: 'B', value: 2, extra: 3 }
    ]} />);
    expect(screen.getByText((content) => content.includes('multiple series') && content.includes('unexpected structure'))).toBeInTheDocument();
  });

  it('renders normal chart for valid data', () => {
    render(<Visualization chartData={[{ name: 'A', value: 1 }, { name: 'B', value: 2 }]} />);
    expect(screen.getByLabelText(/Data Visualization/i)).toBeInTheDocument();
  });

  it('shows loading spinner when loading=true', () => {
    render(<Visualization loading={true} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/Loading chart/i)).toBeInTheDocument();
  });
}); 