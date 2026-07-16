import axe from 'axe-core';

export interface AxeViolation {
  id: string;
  impact: string;
  description: string;
  help: string;
  helpUrl: string;
  nodes: { html: string; failureSummary: string }[];
}

export interface AxeResults {
  violations: AxeViolation[];
  passes: { id: string }[];
  incomplete: { id: string }[];
  inapplicable: { id: string }[];
}

export function runAxe(container: HTMLElement): Promise<AxeResults> {
  return new Promise((resolve, reject) => {
    axe.run(container, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
      },
    }, (err, results) => {
      if (err) reject(err);
      else resolve(results as unknown as AxeResults);
    });
  });
}

export function formatViolations(violations: AxeViolation[]): string {
  return violations.map((v) =>
    `  [${v.impact}] ${v.id}: ${v.description}\n    ${v.help}\n    ${v.helpUrl}\n    Nodes: ${v.nodes.length}`
  ).join('\n');
}
