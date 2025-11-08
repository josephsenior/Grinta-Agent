import React from "react";
import { Github, Heart, Info, Mail, FileText, Shield, ExternalLink } from "lucide-react";
import { BRAND } from "#/config/brand";
import logoImage from "#/assets/branding/logo2.png";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer 
      className="relative z-10 py-12 px-6 border-t border-border bg-background-secondary/50 safe-area-bottom safe-area-left safe-area-right"
      style={{
        paddingBottom: 'max(3rem, env(safe-area-inset-bottom))',
        paddingLeft: 'max(1.5rem, env(safe-area-inset-left))',
        paddingRight: 'max(1.5rem, env(safe-area-inset-right))',
      }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 md:gap-12">
          {/* Brand & Attribution */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <img
                src={logoImage}
                alt="Forge Pro Logo"
                className="w-10 h-10 object-contain"
              />
              <div>
                <span className="text-xl font-bold text-gradient-brand">
                  {BRAND.name}
                </span>
                <p className="text-xs text-foreground-tertiary">
                  {BRAND.tagline}
                </p>
              </div>
            </div>
            
            <p className="text-sm text-foreground-secondary leading-relaxed mb-4">
              {BRAND.description}
            </p>

            {/* MIT Attribution */}
            <div className="p-3 rounded-lg border border-border bg-background-tertiary/50">
              <p className="text-xs text-foreground-tertiary flex items-center gap-2">
                <Heart className="w-3 h-3 text-accent-500" />
                <span>
                  {BRAND.attribution.acknowledgment}
                </span>
              </p>
              <a
                href="https://github.com/All-Hands-AI/Forge"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-accent-500 hover:text-accent-400 transition-colors inline-flex items-center gap-1 mt-1"
              >
                View Forge on GitHub →
              </a>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h3 className="font-semibold text-foreground mb-4 text-sm">
              Product
            </h3>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a
                  href="/about"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <Info className="w-3.5 h-3.5" />
                  About
                </a>
              </li>
              <li>
                <a
                  href="/contact"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <Mail className="w-3.5 h-3.5" />
                  Contact
                </a>
              </li>
              <li>
                <a
                  href={BRAND.urls.docs}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Documentation
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href={BRAND.urls.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <Github className="w-3.5 h-3.5" />
                  GitHub
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h3 className="font-semibold text-foreground mb-4 text-sm">
              Legal
            </h3>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a
                  href="/terms"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Terms of Service
                </a>
              </li>
              <li>
                <a
                  href="/privacy"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <Shield className="w-3.5 h-3.5" />
                  Privacy Policy
                </a>
              </li>
              <li>
                <a
                  href="https://opensource.org/licenses/MIT"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground-secondary hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5" />
                  MIT License
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col md:flex-row items-center justify-between mt-10 pt-6 border-t border-border gap-4">
          <div className="text-sm text-foreground-tertiary text-center md:text-left">
            © {currentYear} {BRAND.name}. All rights reserved.
          </div>
          
          <div className="text-xs text-foreground-tertiary text-center md:text-right">
            <span className="inline-flex items-center gap-1">
              Made with <Heart className="w-3 h-3 text-accent-500 inline" /> for developers
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
