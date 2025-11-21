import { ESLint } from 'eslint';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const complexityConfig = {
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: './tsconfig.json',
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  plugins: ['@typescript-eslint'],
  rules: {
    complexity: ['error', 10] // Find functions with complexity > 10 (C-level and above)
  }
};

async function analyzeComplexity() {
  const eslint = new ESLint({
    baseConfig: complexityConfig,
    useEslintrc: false,
    extensions: ['.ts', '.tsx']
  });

  const results = await eslint.lintFiles(['src/**/*.{ts,tsx}']);
  
  const complexityIssues = [];
  
  for (const result of results) {
    const complexityMessages = result.messages.filter(m => m.ruleId === 'complexity');
    
    if (complexityMessages.length > 0) {
      const fileContent = readFileSync(result.filePath, 'utf-8');
      const lines = fileContent.split('\n');
      
      for (const message of complexityMessages) {
        const line = lines[message.line - 1] || '';
        const functionMatch = line.match(/(?:function|const|export\s+(?:function|const))\s+(\w+)/);
        const functionName = functionMatch ? functionMatch[1] : `Line ${message.line}`;
        
        complexityIssues.push({
          file: result.filePath.replace(process.cwd() + '\\', '').replace(process.cwd() + '/', ''),
          line: message.line,
          column: message.column,
          complexity: parseInt(message.message.match(/\d+/)?.[0] || '0'),
          functionName,
          message: message.message
        });
      }
    }
  }
  
  // Sort by complexity (highest first)
  complexityIssues.sort((a, b) => b.complexity - a.complexity);
  
  // Generate report
  let report = '# Frontend Cyclomatic Complexity Analysis\n\n';
  report += `**Analysis Date:** ${new Date().toISOString()}\n\n`;
  report += `**Total Functions with Complexity > 10:** ${complexityIssues.length}\n\n`;
  
  if (complexityIssues.length === 0) {
    report += '✅ **Excellent!** No functions found with complexity above 10 (C-level).\n';
    report += 'All functions are at B-level (6-10) or A-level (1-5).\n';
  } else {
    report += '## Functions Requiring Refactoring (Complexity > 10)\n\n';
    report += '| File | Function | Line | Complexity | Rating |\n';
    report += '|------|----------|------|------------|--------|\n';
    
    for (const issue of complexityIssues) {
      let rating = 'C';
      if (issue.complexity >= 21 && issue.complexity <= 50) rating = 'D';
      else if (issue.complexity > 50) rating = 'E-F';
      
      report += `| \`${issue.file}\` | \`${issue.functionName}\` | ${issue.line} | ${issue.complexity} | ${rating} |\n`;
    }
    
    // Group by file
    report += '\n## Grouped by File\n\n';
    const byFile = {};
    for (const issue of complexityIssues) {
      if (!byFile[issue.file]) {
        byFile[issue.file] = [];
      }
      byFile[issue.file].push(issue);
    }
    
    for (const [file, issues] of Object.entries(byFile)) {
      report += `### ${file}\n\n`;
      for (const issue of issues) {
        let rating = 'C';
        if (issue.complexity >= 21 && issue.complexity <= 50) rating = 'D';
        else if (issue.complexity > 50) rating = 'E-F';
        
        report += `- **${issue.functionName}** (Line ${issue.line}): Complexity ${issue.complexity} (${rating}-rated)\n`;
      }
      report += '\n';
    }
    
    // Statistics
    const cCount = complexityIssues.filter(i => i.complexity >= 11 && i.complexity <= 20).length;
    const dCount = complexityIssues.filter(i => i.complexity >= 21 && i.complexity <= 50).length;
    const eCount = complexityIssues.filter(i => i.complexity > 50).length;
    
    report += '## Complexity Distribution\n\n';
    report += `- **C-rated (11-20):** ${cCount} functions\n`;
    report += `- **D-rated (21-50):** ${dCount} functions\n`;
    report += `- **E-F-rated (>50):** ${eCount} functions\n\n`;
  }
  
  // Write report
  const reportPath = join(process.cwd(), 'COMPLEXITY_ANALYSIS.md');
  writeFileSync(reportPath, report, 'utf-8');
  
  console.log('Complexity analysis complete!');
  console.log(`Found ${complexityIssues.length} functions with complexity > 10`);
  console.log(`Report saved to: ${reportPath}`);
  
  if (complexityIssues.length > 0) {
    console.log('\nTop 10 most complex functions:');
    complexityIssues.slice(0, 10).forEach((issue, idx) => {
      console.log(`${idx + 1}. ${issue.functionName} in ${issue.file} (Line ${issue.line}): ${issue.complexity}`);
    });
  }
}

analyzeComplexity().catch(console.error);

