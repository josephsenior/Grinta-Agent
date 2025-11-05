import React from 'react';
import { render, screen } from '@testing-library/react';
import { FileExplorer } from '../file-explorer';

// Mock the OpenHands API
jest.mock('#/api/open-hands', () => ({
  OpenHands: {
    getFiles: jest.fn().mockResolvedValue([
      'src/components/App.tsx',
      'src/utils/helpers.ts',
      'README.md',
      'package.json'
    ])
  }
}));

// Mock the useTranslation hook
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key
  })
}));

describe('FileExplorer', () => {
  it('renders without crashing', () => {
    render(
      <FileExplorer
        conversationId="test-conversation"
        onFileSelect={() => {}}
        onFileOpen={() => {}}
        onFileDelete={() => {}}
        onFileRename={() => {}}
      />
    );
    
    expect(screen.getByText('Files')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    render(
      <FileExplorer
        conversationId="test-conversation"
        onFileSelect={() => {}}
        onFileOpen={() => {}}
        onFileDelete={() => {}}
        onFileRename={() => {}}
      />
    );
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
