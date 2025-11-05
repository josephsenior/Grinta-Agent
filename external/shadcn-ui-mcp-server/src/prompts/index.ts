import { getFramework } from '../utils/framework.js';
import { getOptimizationInstructions, getPageTypeSpecificInstructions } from './helpers.js';

/**
 * List of prompts metadata available in this MCP server
 * Each prompt must have a name, description, and arguments if parameters are needed
 */
export const prompts = {
  'build-shadcn-page': {
    name: 'build-shadcn-page',
    description: 'Generate a complete shadcn/ui page using v4 components and blocks',
    arguments: [
      {
        name: 'pageType',
        description:
          'Type of page to build (dashboard, login, calendar, sidebar, products, custom)',
        required: true,
      },
      {
        name: 'features',
        description: 'Specific features or components needed (comma-separated)',
      },
      {
        name: 'layout',
        description: 'Layout preference (sidebar, header, full-width, centered)',
      },
      {
        name: 'style',
        description: 'Design style (minimal, modern, enterprise, creative)',
      },
    ],
  },
  'create-dashboard': {
    name: 'create-dashboard',
    description: 'Create a comprehensive dashboard using shadcn/ui v4 blocks and components',
    arguments: [
      {
        name: 'dashboardType',
        description: 'Type of dashboard (analytics, admin, user, project, sales)',
        required: true,
      },
      {
        name: 'widgets',
        description: 'Dashboard widgets needed (charts, tables, cards, metrics)',
      },
      {
        name: 'navigation',
        description: 'Navigation style (sidebar, top-nav, breadcrumbs)',
      },
    ],
  },
  'create-auth-flow': {
    name: 'create-auth-flow',
    description: 'Generate authentication pages using shadcn/ui v4 login blocks',
    arguments: [
      {
        name: 'authType',
        description: 'Authentication type (login, register, forgot-password, two-factor)',
        required: true,
      },
      {
        name: 'providers',
        description: 'Auth providers (email, google, github, apple)',
      },
      {
        name: 'features',
        description: 'Additional features (remember-me, social-login, validation)',
      },
    ],
  },
  'optimize-shadcn-component': {
    name: 'optimize-shadcn-component',
    description: 'Optimize or enhance existing shadcn/ui components with best practices',
    arguments: [
      {
        name: 'component',
        description: 'Component name to optimize',
        required: true,
      },
      {
        name: 'optimization',
        description: 'Type of optimization (performance, accessibility, responsive, animations)',
      },
      {
        name: 'useCase',
        description: 'Specific use case or context for the component',
      },
    ],
  },
  'create-data-table': {
    name: 'create-data-table',
    description: 'Create advanced data tables with shadcn/ui components',
    arguments: [
      {
        name: 'dataType',
        description: 'Type of data to display (users, products, orders, analytics)',
        required: true,
      },
      {
        name: 'features',
        description: 'Table features (sorting, filtering, pagination, search, selection)',
      },
      {
        name: 'actions',
        description: 'Row actions (edit, delete, view, custom)',
      },
    ],
  },
};

/**
 * Map of prompt names to their handler functions
 * Each handler generates the actual prompt content with the provided parameters
 */
export const promptHandlers = {
  'build-shadcn-page': ({
    pageType,
    features = '',
    layout = 'sidebar',
    style = 'modern',
  }: {
    pageType: string;
    features?: string;
    layout?: string;
    style?: string;
  }) => {
    const framework = getFramework();

    return {
      messages: [
        {
          role: 'user',
          content: {
            type: 'text',
            text: `Create a complete ${pageType} page using shadcn/ui v4 components and blocks for ${framework}.

REQUIREMENTS:
- Framework: ${framework}
- Page Type: ${pageType}
- Features: ${features || 'Standard features for this page type'}
- Layout: ${layout}
- Design Style: ${style}

INSTRUCTIONS:
1. Use the MCP tools to explore available v4 blocks for this page type:
   - Use 'list_blocks' to see available categories
   - Use 'get_block' to fetch specific block implementations

2. Build the page following these principles:
   - Use shadcn/ui v4 components and blocks as building blocks
   - Ensure responsive design with Tailwind CSS classes
   - Implement proper TypeScript types
   - Follow ${framework} best practices and conventions
   - Include proper accessibility attributes

3. For ${pageType} pages specifically:
   ${getPageTypeSpecificInstructions(pageType)}

4. Code Structure:
   - Create a main page component using ${framework} patterns
   - Use sub-components for complex sections
   - Include proper imports from shadcn/ui registry
   - Add necessary state management with ${framework} best practices
   - Include proper error handling

5. Styling Guidelines:
   - Use consistent spacing and typography
   - Implement ${style} design principles
   - Ensure dark/light mode compatibility
   - Use shadcn/ui design tokens

Please provide complete, production-ready ${framework} code with proper imports and TypeScript types.`,
          },
        },
      ],
    };
  },

  'create-dashboard': ({
    dashboardType,
    widgets = 'charts,tables,cards',
    navigation = 'sidebar',
  }: {
    dashboardType: string;
    widgets?: string;
    navigation?: string;
  }) => {
    const framework = getFramework();

    return {
      messages: [
        {
          role: 'user',
          content: {
            type: 'text',
            text: `Create a comprehensive ${dashboardType} dashboard using shadcn/ui v4 blocks and components for ${framework}.

REQUIREMENTS:
- Framework: ${framework}
- Dashboard Type: ${dashboardType}
- Widgets: ${widgets}
- Navigation: ${navigation}

INSTRUCTIONS:
1. First, explore available dashboard blocks:
   - Use 'list_blocks' with category="dashboard" to see available dashboard blocks
   - Use 'get_block' to examine dashboard-01 and other dashboard implementations
   - Study the structure and component usage

2. Dashboard Structure:
   - Implement ${navigation} navigation using appropriate shadcn/ui components
   - Create a responsive grid layout for widgets
   - Include proper header with user menu and notifications
   - Add breadcrumb navigation

3. Widgets to Include:
   ${widgets
     .split(',')
     .map((widget) => `- ${widget.trim()} with real-time data simulation`)
     .join('\n   ')}

4. Key Features:
   - Responsive design that works on mobile, tablet, and desktop
   - Interactive charts using a charting library compatible with shadcn/ui
   - Data tables with sorting, filtering, and pagination
   - Modal dialogs for detailed views
   - Toast notifications for user feedback

5. Data Management:
   - Create mock data structures for ${dashboardType}
   - Implement state management with ${framework} best practices
   - Add loading states and error handling
   - Include data refresh functionality

6. Accessibility:
   - Proper ARIA labels and roles
   - Keyboard navigation support
   - Screen reader compatibility
   - Color contrast compliance

Provide complete ${framework} code with all necessary imports, types, and implementations.`,
          },
        },
      ],
    };
  },

  'create-auth-flow': ({
    authType,
    providers = 'email',
    features = 'validation',
  }: {
    authType: string;
    providers?: string;
    features?: string;
  }) => {
    const framework = getFramework();

    return {
      messages: [
        {
          role: 'user',
          content: {
            type: 'text',
            text: `Create a complete ${authType} authentication flow using shadcn/ui v4 login blocks and components for ${framework}.

REQUIREMENTS:
- Framework: ${framework}
- Auth Type: ${authType}
- Providers: ${providers}
- Features: ${features}

INSTRUCTIONS:
1. Explore login blocks first:
   - Use 'list_blocks' with category="login" to see available login blocks
   - Use 'get_block' to examine login-01, login-02, etc. implementations
   - Study different authentication patterns and layouts

2. Authentication Components:
   - Form validation using ${framework} best practices
   - Input components with proper error states
   - Loading states during authentication
   - Success/error feedback with toast notifications

3. Providers Implementation:
   ${providers
     .split(',')
     .map((provider) => `- ${provider.trim()}: Implement ${provider.trim()} authentication UI`)
     .join('\n   ')}

4. Security Features:
   - Form validation with proper error messages
   - Password strength indicator (if applicable)
   - CSRF protection considerations
   - Secure form submission patterns

5. UX Considerations:
   - Smooth transitions between auth states
   - Clear error messaging
   - Progressive enhancement
   - Mobile-friendly design
   - Remember me functionality (if applicable)

6. Form Features:
   ${features
     .split(',')
     .map((feature) => `- ${feature.trim()}: Implement ${feature.trim()} functionality`)
     .join('\n   ')}

7. Layout Options:
   - Choose appropriate layout from available login blocks
   - Center-aligned forms with proper spacing
   - Background images or gradients (optional)
   - Responsive design for all screen sizes

Provide complete ${framework} authentication flow code with proper TypeScript types, validation, and error handling.`,
          },
        },
      ],
    };
  },

  'optimize-shadcn-component': ({
    component,
    optimization = 'performance',
    useCase = 'general',
  }: {
    component: string;
    optimization?: string;
    useCase?: string;
  }) => {
    const framework = getFramework();

    return {
      messages: [
        {
          role: 'user',
          content: {
            type: 'text',
            text: `Optimize the ${component} shadcn/ui component for ${optimization} and ${useCase} use case in ${framework}.

REQUIREMENTS:
- Framework: ${framework}
- Component: ${component}
- Optimization Focus: ${optimization}
- Use Case: ${useCase}

INSTRUCTIONS:
1. First, analyze the current component:
   - Use 'get_component' to fetch the ${component} source code
   - Use 'get_component_demo' to see current usage examples
   - Use 'get_component_metadata' to understand dependencies

2. Optimization Strategy for ${optimization}:
   ${getOptimizationInstructions(optimization, framework)}

3. Use Case Specific Enhancements for ${useCase}:
   - Analyze how ${component} is typically used in ${useCase} scenarios
   - Identify common patterns and pain points
   - Suggest improvements for better developer experience

4. Implementation:
   - Provide optimized component code
   - Include performance benchmarks or considerations
   - Add proper TypeScript types and interfaces
   - Include usage examples demonstrating improvements

5. Best Practices:
   - Follow ${framework} performance best practices
   - Implement ${framework} optimization patterns where needed
   - Ensure backward compatibility
   - Add comprehensive prop validation

6. Testing Considerations:
   - Suggest test cases for the optimized component
   - Include accessibility testing recommendations
   - Performance testing guidelines

Provide the optimized ${framework} component code with detailed explanations of improvements made.`,
          },
        },
      ],
    };
  },

  'create-data-table': ({
    dataType,
    features = 'sorting,filtering,pagination',
    actions = 'edit,delete',
  }: {
    dataType: string;
    features?: string;
    actions?: string;
  }) => {
    const framework = getFramework();

    return {
      messages: [
        {
          role: 'user',
          content: {
            type: 'text',
            text: `Create an advanced data table for ${dataType} using shadcn/ui v4 components in ${framework}.

REQUIREMENTS:
- Framework: ${framework}
- Data Type: ${dataType}
- Features: ${features}
- Actions: ${actions}

INSTRUCTIONS:
1. Explore table components:
   - Use 'get_component' for 'table' to see the base table implementation
   - Use 'get_component_demo' for 'table' to see usage examples
   - Look for any existing table blocks in the blocks directory

2. Table Structure:
   - Create a reusable DataTable component using ${framework} patterns
   - Define proper TypeScript interfaces for ${dataType} data
   - Implement column definitions with proper typing
   - Add responsive table design

3. Features Implementation:
   ${features
     .split(',')
     .map((feature) => {
       const featureInstructions: Record<string, string> = {
         sorting: '- Column sorting (ascending/descending) with visual indicators',
         filtering: '- Global search and column-specific filters',
         pagination: '- Page-based navigation with configurable page sizes',
         search: '- Real-time search across all columns',
         selection: '- Row selection with bulk actions support',
       };
       return (
         featureInstructions[feature.trim()] ||
         `- ${feature.trim()}: Implement ${feature.trim()} functionality`
       );
     })
     .join('\n   ')}

4. Row Actions:
   ${actions
     .split(',')
     .map(
       (action) =>
         `- ${action.trim()}: Implement ${action.trim()} action with proper confirmation dialogs`
     )
     .join('\n   ')}

5. Data Management:
   - Create mock data for ${dataType}
   - Implement data fetching patterns using ${framework} best practices
   - Add loading states and error handling
   - Add optimistic updates for actions
   - Include data validation

6. UI/UX Features:
   - Loading skeletons during data fetch
   - Empty states when no data is available
   - Error states with retry functionality
   - Responsive design for mobile devices
   - Keyboard navigation support

7. Advanced Features:
   - Column resizing and reordering
   - Export functionality (CSV, JSON)
   - Bulk operations
   - Virtual scrolling for large datasets (if needed)

Provide complete ${framework} data table implementation with proper TypeScript types, mock data, and usage examples.`,
          },
        },
      ],
    };
  },
};
