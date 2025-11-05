// Schema definitions for shadcn/ui components
export interface ComponentExample {
  title: string;
  code: string;
  url?: string;
}

export interface ComponentProp {
  name: string;
  type: string;
  description: string;
  required?: boolean;
  default?: string;
}

export interface ComponentInfo {
  name: string;
  description: string;
  url?: string;
  props?: ComponentProp[];
  examples?: ComponentExample[];
  source?: string;
  installation?: string;
}

export interface Theme {
  name: string;
  description: string;
  url?: string;
}

export interface Block {
  name: string;
  description: string;
  url?: string;
  preview?: string;
}
