import '@testing-library/jest-dom';
// Mock ResizeObserver for recharts and other libraries
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver; 