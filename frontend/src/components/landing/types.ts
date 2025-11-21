/**
 * Type definitions for landing page components
 */

export interface NavigationItem {
  name: string;
  href: string;
}

export interface Plan {
  name: string;
  price: string;
  description: string;
  features: string[];
  cta: string;
  popular: boolean;
}

export interface TestimonialData {
  id: number;
  name: string;
  title: string;
  avatar: string;
  content: string;
  rating: number;
}

export interface SocialLink {
  name: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  href: string;
}

export interface FooterLink {
  name: string;
  href: string;
}

export interface FooterLinks {
  product: FooterLink[];
  company: FooterLink[];
  resources: FooterLink[];
  legal: FooterLink[];
}
