import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import userEvent from '@testing-library/user-event';

// Mock fetch for upload and query
beforeEach(() => {
  global.fetch = jest.fn((url, options) => {
    if (url.includes('/upload')) {
      if (options && options.body && options.body.get('file').name.endsWith('.csv')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ filename: options.body.get('file').name, status: 'success' })
        });
      } else {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Upload failed' })
        });
      }
    }
    if (url.includes('/query')) {
      if (options && options.body && options.body.includes('error')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Query failed' })
        });
      }
      if (options && options.body && options.body.includes('What is in the CSV?')) {
        if (global.window && window.innerWidth === 375) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              response: {
                result: JSON.stringify({
                  summary: 'This is a summary.',
                  chartData: [
                    { name: 'A', value: 1 },
                    { name: 'B', value: 2 }
                  ]
                }),
                thinking_steps: [
                  { type: 'thinking', content: 'Step 1' },
                  { type: 'conclusion', content: 'Final answer' }
                ]
              }
            })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            response: {
              result: JSON.stringify({
                summary: 'This is a summary.',
                chartData: [
                  { name: 'A', value: 1 },
                  { name: 'B', value: 2 }
                ]
              }),
              thinking_steps: [
                { type: 'thinking', content: 'Step 1' },
                { type: 'conclusion', content: 'Final answer' }
              ]
            }
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          response: {
            result: JSON.stringify({
              chartData: [
                { name: 'A', value: 1 },
                { name: 'B', value: 2 }
              ]
            }),
            thinking_steps: [
              { type: 'thinking', content: 'Step 1' },
              { type: 'conclusion', content: 'Final answer' }
            ]
          }
        })
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  }) as jest.Mock;
});
afterEach(() => { jest.resetAllMocks(); });

test('renders upload UI and hint', () => {
  render(<App />);
  expect(screen.getByText(/Upload Document/i)).toBeInTheDocument();
  expect(screen.getByText((content) => content.includes('Only CSV files are supported'))).toBeInTheDocument();
});

test('accepts only CSV files and shows error for non-CSV', async () => {
  render(<App />);
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  // Try to upload a .txt file
  const txtFile = new File(['test'], 'test.txt', { type: 'text/plain' });
  fireEvent.change(fileInput, { target: { files: [txtFile] } });
  // There should now be two elements with the hint: the static hint and the error message
  const allHints = await screen.findAllByText((content) => content.includes('Only CSV files are supported'));
  expect(allHints.length).toBeGreaterThanOrEqual(2);
  // Optionally, check that one has class 'error' (the error message)
  expect(allHints.some(el => el.className.includes('error'))).toBe(true);
});

test('shows uploaded CSV in the list', async () => {
  render(<App />);
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
});

test('user can submit a query and receive a summary', async () => {
  render(<App />);
  // Simulate upload
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Submit query
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText('This is a summary.')).toBeInTheDocument());
});

test('shows thinking steps if present in response', async () => {
  render(<App />);
  // Simulate upload
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Submit query
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'Show thinking' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText('Step 1')).toBeInTheDocument());
  expect(screen.getByText('Final answer')).toBeInTheDocument();
});

test('shows error if backend/query fails', async () => {
  render(<App />);
  // Simulate upload
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Submit query that triggers error
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'error' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText(/Query failed/i)).toBeInTheDocument());
});

test('shows upload error for non-CSV file', async () => {
  render(<App />);
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const txtFile = new File(['test'], 'test.txt', { type: 'text/plain' });
  fireEvent.change(fileInput, { target: { files: [txtFile] } });
  // There should be two elements: the static hint and the error
  const allHints = await screen.findAllByText((content) => content.includes('Only CSV files are supported'));
  expect(allHints.length).toBeGreaterThanOrEqual(2);
  expect(allHints.some(el => el.className.includes('error'))).toBe(true);
});

test('shows loading spinner during query', async () => {
  render(<App />);
  // Upload a CSV first
  const fileInput = screen.getByText((content) => content.includes('Only CSV files are supported')).parentElement?.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Start a query
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  // Spinner should appear
  expect(await screen.findByText(/Loading analysis/i)).toBeInTheDocument();
  // Wait for result
  await waitFor(() => expect(screen.getByText('This is a summary.')).toBeInTheDocument());
});

test('shows query error in results', async () => {
  render(<App />);
  // Upload a CSV first
  const fileInput = screen.getByText((content) => content.includes('Only CSV files are supported')).parentElement?.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Submit a query that triggers error
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'error' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText(/Query failed/i)).toBeInTheDocument());
});

test('resets upload error on new valid upload', async () => {
  render(<App />);
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  // Trigger error
  const txtFile = new File(['test'], 'test.txt', { type: 'text/plain' });
  fireEvent.change(fileInput, { target: { files: [txtFile] } });
  const allHints = await screen.findAllByText((content) => content.includes('Only CSV files are supported'));
  expect(allHints.length).toBeGreaterThanOrEqual(2);
  expect(allHints.some(el => el.className.includes('error'))).toBe(true);
  // Upload valid CSV
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // After valid upload, only the static hint should remain
  const hintsAfter = screen.getAllByText((content) => content.includes('Only CSV files are supported'));
  expect(hintsAfter.some(el => el.className.includes('error'))).toBe(false);
});

test('integration: full user journey', async () => {
  render(<App />);
  // Upload valid CSV
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Submit query
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText('This is a summary.')).toBeInTheDocument());
  // See thinking steps
  expect(screen.getByText('Step 1')).toBeInTheDocument();
  expect(screen.getByText('Final answer')).toBeInTheDocument();
  // Trigger error
  fireEvent.change(queryInput, { target: { value: 'error' } });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText(/Query failed/i)).toBeInTheDocument());
  // Recover with new valid query
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText('This is a summary.')).toBeInTheDocument());
});

test('responsiveness: chart and main UI visible at mobile width', async () => {
  render(<App />);
  // Upload valid CSV and submit query
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  fireEvent.click(submitBtn);
  await waitFor(() => expect(screen.getByText('This is a summary.')).toBeInTheDocument());
  // Simulate mobile width
  window.innerWidth = 375;
  window.dispatchEvent(new Event('resize'));
  // Chart and main UI should still be visible
  expect(screen.getByText(/Data Visualization/i)).toBeVisible();
  expect(screen.getByText('Upload Document')).toBeVisible();
  expect(screen.getByText('Ask a Question')).toBeVisible();
  expect(screen.getByText('Results')).toBeVisible();
});

test('accessibility: main sections have headings and keyboard navigation is possible', async () => {
  render(<App />);
  // Headings
  expect(screen.getByRole('heading', { name: /Upload Document/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /Ask a Question/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /Results/i })).toBeInTheDocument();
  // Upload a CSV so inputs are enabled
  const user = userEvent;
  const hintElem = screen.getByText((content) => content.includes('Only CSV files are supported'));
  const fileInput = hintElem.parentElement && hintElem.parentElement.querySelector('input[type="file"]');
  if (!fileInput) throw new Error('File input not found');
  (fileInput as HTMLElement).focus();
  expect(fileInput).toHaveFocus();
  const csvFile = new File(['col1,col2\n1,2'], 'test.csv', { type: 'text/csv' });
  fireEvent.change(fileInput, { target: { files: [csvFile] } });
  await waitFor(() => expect(screen.getByText('test.csv')).toBeInTheDocument());
  // Enter a query so submit button is enabled
  const queryInput = screen.getByPlaceholderText(/Enter your question/i);
  fireEvent.change(queryInput, { target: { value: 'What is in the CSV?' } });
  await user.tab();
  expect(queryInput).toHaveFocus();
  await user.tab();
  const submitBtn = screen.getByRole('button', { name: /submit query/i });
  expect(submitBtn).toHaveFocus();
});
