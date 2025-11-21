import { Github, Twitter, Linkedin, Mail } from "lucide-react";
import { Link } from "react-router-dom";
import type { FooterLinks, SocialLink } from "./types";

const footerLinks: FooterLinks = {
  product: [
    { name: "Features", href: "#features" },
    { name: "Pricing", href: "#pricing" },
    { name: "Security", href: "/privacy" },
    { name: "Roadmap", href: "/about" },
  ],
  company: [
    { name: "About", href: "/about" },
    { name: "Blog", href: "#" },
    { name: "Careers", href: "#" },
    { name: "Press", href: "#" },
  ],
  resources: [
    { name: "Documentation", href: "/help" },
    { name: "API Reference", href: "/help" },
    { name: "Guides", href: "/help" },
    { name: "Community", href: "#" },
  ],
  legal: [
    { name: "Privacy", href: "/privacy" },
    { name: "Terms", href: "/terms" },
    { name: "Cookie Policy", href: "/privacy" },
    { name: "Licenses", href: "#" },
  ],
};

const socialLinks: SocialLink[] = [
  { name: "GitHub", icon: Github, href: "https://github.com" },
  { name: "Twitter", icon: Twitter, href: "https://twitter.com" },
  { name: "LinkedIn", icon: Linkedin, href: "https://linkedin.com" },
  { name: "Email", icon: Mail, href: "mailto:support@forge.dev" },
];

export default function Footer() {
  const handleLinkClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  };

  return (
    <footer
      className="w-full border-t border-border-subtle"
      style={{ backgroundColor: "var(--bg-primary)" }}
    >
      <div className="w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-5 gap-8 lg:gap-12 mb-12 min-w-0 w-full items-start">
          <div className="w-full">
            <Link to="/" className="flex items-center gap-2 mb-6 w-full">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-violet to-brand-violet-dark flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-lg">F</span>
              </div>
              <span
                className="text-xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                Forge
              </span>
            </Link>
            <p className="text-text-tertiary text-sm mb-6 w-full">
              Building the future of AI-powered development, one deployment at a
              time.
            </p>
            <div className="flex gap-4 w-full">
              {socialLinks.map((social) => {
                const Icon = social.icon;
                return (
                  <a
                    key={social.name}
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-10 h-10 rounded-lg flex items-center justify-center transition-colors duration-200 flex-shrink-0"
                    style={{
                      backgroundColor: "var(--bg-tertiary)",
                    }}
                    onMouseEnter={(e) => {
                      const target = e.currentTarget;
                      target.style.backgroundColor = "var(--bg-elevated)";
                    }}
                    onMouseLeave={(e) => {
                      const target = e.currentTarget;
                      target.style.backgroundColor = "var(--bg-tertiary)";
                    }}
                    aria-label={social.name}
                  >
                    <Icon size={18} className="text-text-tertiary" />
                  </a>
                );
              })}
            </div>
          </div>

          <div className="w-full flex flex-col">
            <h3
              className="font-semibold mb-4 w-full"
              style={{ color: "var(--text-primary)" }}
            >
              Product
            </h3>
            <ul className="space-y-3 w-full">
              {footerLinks.product.map((link) => (
                <li key={link.name} className="w-full">
                  {link.href.startsWith("#") ? (
                    <a
                      href={link.href}
                      onClick={(e) => handleLinkClick(e, link.href)}
                      className="transition-colors duration-200 text-sm w-full block"
                      style={{ color: "var(--text-tertiary)" }}
                      onMouseEnter={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-primary)";
                      }}
                      onMouseLeave={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-tertiary)";
                      }}
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-text-tertiary hover:text-white transition-colors duration-200 text-sm w-full block"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="w-full flex flex-col">
            <h3
              className="font-semibold mb-4 w-full"
              style={{ color: "var(--text-primary)" }}
            >
              Company
            </h3>
            <ul className="space-y-3 w-full">
              {footerLinks.company.map((link) => (
                <li key={link.name} className="w-full">
                  {link.href.startsWith("#") ? (
                    <a
                      href={link.href}
                      onClick={(e) => handleLinkClick(e, link.href)}
                      className="transition-colors duration-200 text-sm w-full block"
                      style={{ color: "var(--text-tertiary)" }}
                      onMouseEnter={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-primary)";
                      }}
                      onMouseLeave={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-tertiary)";
                      }}
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-text-tertiary hover:text-white transition-colors duration-200 text-sm w-full block"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="w-full flex flex-col">
            <h3
              className="font-semibold mb-4 w-full"
              style={{ color: "var(--text-primary)" }}
            >
              Resources
            </h3>
            <ul className="space-y-3 w-full">
              {footerLinks.resources.map((link) => (
                <li key={link.name} className="w-full">
                  {link.href.startsWith("#") ? (
                    <a
                      href={link.href}
                      onClick={(e) => handleLinkClick(e, link.href)}
                      className="transition-colors duration-200 text-sm w-full block"
                      style={{ color: "var(--text-tertiary)" }}
                      onMouseEnter={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-primary)";
                      }}
                      onMouseLeave={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-tertiary)";
                      }}
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-text-tertiary hover:text-white transition-colors duration-200 text-sm w-full block"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="w-full flex flex-col">
            <h3
              className="font-semibold mb-4 w-full"
              style={{ color: "var(--text-primary)" }}
            >
              Legal
            </h3>
            <ul className="space-y-3 w-full">
              {footerLinks.legal.map((link) => (
                <li key={link.name} className="w-full">
                  {link.href.startsWith("#") ? (
                    <a
                      href={link.href}
                      onClick={(e) => handleLinkClick(e, link.href)}
                      className="transition-colors duration-200 text-sm w-full block"
                      style={{ color: "var(--text-tertiary)" }}
                      onMouseEnter={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-primary)";
                      }}
                      onMouseLeave={(e) => {
                        const target = e.currentTarget;
                        target.style.color = "var(--text-tertiary)";
                      }}
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-text-tertiary hover:text-white transition-colors duration-200 text-sm w-full block"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-border-subtle w-full">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 w-full">
            <p className="text-text-tertiary text-sm w-full md:w-auto">
              &copy; {new Date().getFullYear()} Forge. All rights reserved.
            </p>
            <div className="flex items-center gap-2 text-sm text-text-tertiary w-full md:w-auto justify-center md:justify-end">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse flex-shrink-0" />
              <span className="w-full">All systems operational</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
