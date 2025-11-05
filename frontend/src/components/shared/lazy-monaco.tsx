import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load Monaco Editor to reduce initial bundle size
const MonacoEditor = React.lazy(() => import('@monaco-editor/react'));

interface LazyMonacoProps {
  value: string;
  onChange?: (value: string | undefined) => void;
  language?: string;
  height?: string;
  theme?: string;
  options?: Record<string, unknown>;
  onMount?: (editor: unknown, monaco: unknown) => void;
  beforeMount?: (monaco: unknown) => void;
}

/**
 * Lazy-loaded Monaco Editor wrapper with loading state
 * Reduces initial bundle size by ~1.5MB
 */
export function LazyMonaco({
  value,
  onChange,
  language = 'sql',
  height = '400px',
  theme = 'vs-dark',
  options = {},
  onMount,
  beforeMount,
}: LazyMonacoProps) {
  return (
    <Suspense
      fallback={
        <div 
          className="flex items-center justify-center bg-gray-900 rounded-lg"
          style={{ height }}
        >
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            <p className="text-sm text-gray-400">Loading editor...</p>
          </div>
        </div>
      }
    >
      <MonacoEditor
        value={value}
        onChange={onChange}
        language={language}
        height={height}
        theme={theme}
        onMount={onMount}
        beforeMount={beforeMount}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          ...options,
        }}
      />
    </Suspense>
  );
}

